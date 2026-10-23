package dev.voxhash.voxplayer.companion

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.SkipNext
import androidx.compose.material.icons.filled.SkipPrevious
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.media3.ui.PlayerView

private val Accent = Color(0xFF5B8DEF)
private val ActiveGreen = Color(0xFF1DB954)
private val Bg = Color(0xFF12141A)
private val SurfaceCol = Color(0xFF1A2030)

class MainActivity : ComponentActivity() {
    private val vm: PlayerViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleViewIntent(intent)
        val extras = intent?.extras
        if (extras != null) {
            val host = extras.getString("host").orEmpty()
            val port = extras.getString("port").orEmpty()
            val autoconnect = extras.getBoolean("autoconnect", false) ||
                extras.getString("autoconnect").equals("1", true) ||
                extras.getString("autoconnect").equals("true", true)
            if (host.isNotBlank() || port.isNotBlank() || autoconnect) {
                if (host.isNotBlank()) vm.updateRemoteHost(host)
                if (port.isNotBlank()) vm.updateRemotePort(port)
                if (autoconnect) vm.connectManual()
            }
        }
        enableEdgeToEdge()
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = Accent,
                    background = Bg,
                    surface = SurfaceCol,
                ),
            ) {
                Surface(Modifier.fillMaxSize()) {
                    VoxPlayerApp(vm)
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleViewIntent(intent)
    }

    private fun handleViewIntent(intent: Intent?) {
        if (intent?.action == Intent.ACTION_VIEW) {
            val uri = intent.data ?: return
            val mime = intent.type ?: contentResolver.getType(uri) ?: ""
            val isVideo = mime.startsWith("video")
            vm.playUri(uri, uri.lastPathSegment ?: "Media", isVideo)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VoxPlayerApp(vm: PlayerViewModel) {
    val state by vm.state.collectAsState()
    val context = LocalContext.current

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { vm.reloadLocalLibrary() }

    val openDoc = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri != null) {
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION,
                )
            } catch (_: Exception) {
            }
            val mime = context.contentResolver.getType(uri) ?: ""
            vm.playUri(uri, uri.lastPathSegment ?: "Media", mime.startsWith("video"))
        }
    }

    LaunchedEffect(Unit) {
        if (vm.hasMediaPermission()) vm.reloadLocalLibrary()
        else {
            val perms = if (Build.VERSION.SDK_INT >= 33) {
                arrayOf(
                    Manifest.permission.READ_MEDIA_AUDIO,
                    Manifest.permission.READ_MEDIA_VIDEO,
                )
            } else {
                arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE)
            }
            permissionLauncher.launch(perms)
        }
    }

    Scaffold(
        containerColor = Bg,
        bottomBar = {
            TransportBar(
                state = state,
                onConnect = { vm.openConnect(true) },
                onPlayPause = {
                    if (state.activeOutput.startsWith("Desktop")) vm.remotePlayPause()
                    else vm.localPlayPause()
                },
            )
        },
    ) { pad ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(pad)
                .padding(horizontal = 16.dp),
        ) {
            Row(
                Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("VoxPlayer", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.SemiBold)
                Row {
                    FilterChip(
                        selected = state.tab == AppTab.Local,
                        onClick = { vm.setTab(AppTab.Local) },
                        label = { Text("This device") },
                    )
                    Spacer(Modifier.size(8.dp))
                    FilterChip(
                        selected = state.tab == AppTab.Connect,
                        onClick = { vm.setTab(AppTab.Connect) },
                        label = { Text("Desktop") },
                    )
                }
            }

            if (state.error.isNotBlank()) {
                Text(state.error, color = Color(0xFFE26D6D), modifier = Modifier.padding(bottom = 8.dp))
            }

            when (state.tab) {
                AppTab.Local -> LocalTab(
                    state = state,
                    player = vm.player,
                    onPlay = vm::playLocal,
                    onFilter = vm::setLocalFilter,
                    onOpenFile = { openDoc.launch(arrayOf("audio/*", "video/*")) },
                    onRequestPerm = {
                        val perms = if (Build.VERSION.SDK_INT >= 33) {
                            arrayOf(Manifest.permission.READ_MEDIA_AUDIO, Manifest.permission.READ_MEDIA_VIDEO)
                        } else arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE)
                        permissionLauncher.launch(perms)
                    },
                    onSeekBack = { vm.localSeekBy(-5000) },
                    onSeekFwd = { vm.localSeekBy(5000) },
                    onStop = vm::localStop,
                )
                AppTab.Connect -> DesktopRemoteTab(state, vm)
            }
        }
    }

    if (state.connectOpen) {
        ModalBottomSheet(
            onDismissRequest = { vm.openConnect(false) },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            containerColor = SurfaceCol,
        ) {
            ConnectSheet(state, vm)
        }
    }
}

@Composable
private fun TransportBar(
    state: PlayerUiState,
    onConnect: () -> Unit,
    onPlayPause: () -> Unit,
) {
    val playing = if (state.activeOutput.startsWith("Desktop")) state.remotePlaying else state.localPlaying
    val title = if (state.activeOutput.startsWith("Desktop")) state.remoteTitle else state.localTitle
    val pos = if (state.activeOutput.startsWith("Desktop")) state.remotePositionLabel else state.localPositionLabel
    Row(
        Modifier
            .fillMaxWidth()
            .background(SurfaceCol)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, maxLines = 1, fontWeight = FontWeight.Medium)
            Text("$pos · ${state.activeOutput}", color = Color.White.copy(0.55f), style = MaterialTheme.typography.bodySmall)
        }
        IconButton(onClick = onPlayPause) {
            Icon(if (playing) Icons.Default.Pause else Icons.Default.PlayArrow, contentDescription = "Play/Pause")
        }
        IconButton(onClick = onConnect) {
            Icon(
                Icons.Default.Devices,
                contentDescription = "Connect",
                tint = if (state.activeOutput.startsWith("Desktop")) ActiveGreen else Color.White,
            )
        }
    }
}

@Composable
private fun LocalTab(
    state: PlayerUiState,
    player: androidx.media3.exoplayer.ExoPlayer,
    onPlay: (LocalMediaItem) -> Unit,
    onFilter: (String) -> Unit,
    onOpenFile: () -> Unit,
    onRequestPerm: () -> Unit,
    onSeekBack: () -> Unit,
    onSeekFwd: () -> Unit,
    onStop: () -> Unit,
) {
    if (state.permissionNeeded) {
        Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Allow access to music and videos to play files on this device.")
            Text(
                "GrapheneOS: you can use Storage Scopes or grant media permissions; Open file works via the system picker without broad access.",
                color = Color.White.copy(0.6f),
            )
            Button(onClick = onRequestPerm) { Text("Grant media access") }
            Button(onClick = onOpenFile) { Text("Open file…") }
        }
        return
    }

    if (state.localIsVideo && (state.localPlaying || state.localTitle != "(nothing loaded)")) {
        AndroidView(
            factory = { ctx ->
                PlayerView(ctx).apply {
                    this.player = player
                    useController = false
                }
            },
            update = { it.player = player },
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(16f / 9f)
                .background(Color.Black),
        )
        Spacer(Modifier.height(8.dp))
    }

    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        listOf("all" to "All", "audio" to "Audio", "video" to "Video").forEach { (k, label) ->
            FilterChip(selected = state.localFilter == k, onClick = { onFilter(k) }, label = { Text(label) })
        }
        Spacer(Modifier.weight(1f))
        IconButton(onClick = onOpenFile) { Icon(Icons.Default.FolderOpen, contentDescription = "Open") }
    }

    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Button(onClick = onSeekBack, modifier = Modifier.weight(1f)) { Text("−5s") }
        Button(onClick = onStop, modifier = Modifier.weight(1f)) { Text("Stop") }
        Button(onClick = onSeekFwd, modifier = Modifier.weight(1f)) { Text("+5s") }
    }

    val filtered = remember(state.localItems, state.localFilter) {
        when (state.localFilter) {
            "audio" -> state.localItems.filter { !it.isVideo }
            "video" -> state.localItems.filter { it.isVideo }
            else -> state.localItems
        }
    }

    Text("On this device (${filtered.size})", fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(vertical = 8.dp))
    LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        items(filtered, key = { "${it.isVideo}-${it.id}" }) { item ->
            Column(
                Modifier
                    .fillMaxWidth()
                    .clickable { onPlay(item) }
                    .padding(vertical = 8.dp),
            ) {
                Text(item.title, maxLines = 1)
                Text(
                    buildString {
                        if (item.artist.isNotBlank()) append(item.artist).append(" · ")
                        append(if (item.isVideo) "Video" else "Audio")
                    },
                    color = Color.White.copy(0.55f),
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

@Composable
private fun DesktopRemoteTab(state: PlayerUiState, vm: PlayerViewModel) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxSize()) {
        Text(
            if (state.remoteConnected) "Connected · desktop v${state.remoteVersion.ifBlank { "?" }}"
            else "Not connected — tap the devices icon to Connect",
            color = if (state.remoteConnected) ActiveGreen else Color(0xFFE26D6D),
        )
        Text("[${if (state.remotePlaying) "PLAYING" else "PAUSED"}] ${state.remoteTitle}")
        Text("${state.remotePositionLabel} · vol ${state.remoteVolume}%")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = vm::remotePrev, modifier = Modifier.weight(1f)) {
                Icon(Icons.Default.SkipPrevious, null)
            }
            Button(onClick = vm::remotePlayPause, modifier = Modifier.weight(1f)) {
                Icon(if (state.remotePlaying) Icons.Default.Pause else Icons.Default.PlayArrow, null)
            }
            Button(onClick = vm::remoteNext, modifier = Modifier.weight(1f)) {
                Icon(Icons.Default.SkipNext, null)
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = vm::remoteStop, modifier = Modifier.weight(1f)) { Icon(Icons.Default.Stop, null) }
            Button(onClick = vm::remoteSeekBack, modifier = Modifier.weight(1f)) { Text("−5s") }
            Button(onClick = vm::remoteSeekFwd, modifier = Modifier.weight(1f)) { Text("+5s") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = vm::remoteVolDown, modifier = Modifier.weight(1f)) { Text("Vol −") }
            Button(onClick = vm::remoteVolUp, modifier = Modifier.weight(1f)) { Text("Vol +") }
            Button(onClick = { vm.openConnect(true) }, modifier = Modifier.weight(1f)) { Text("Connect") }
        }
        Text("Desktop library", fontWeight = FontWeight.SemiBold)
        LazyColumn(Modifier.weight(1f)) {
            items(state.remoteLibrary.take(80)) { item ->
                Text(
                    item.title,
                    Modifier
                        .fillMaxWidth()
                        .clickable { vm.remoteOpen(item.path) }
                        .padding(vertical = 6.dp),
                )
            }
        }
    }
}

@Composable
private fun ConnectSheet(state: PlayerUiState, vm: PlayerViewModel) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(start = 20.dp, end = 20.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Connect", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
            IconButton(onClick = { vm.openConnect(false) }) {
                Icon(Icons.Default.Close, contentDescription = "Close")
            }
        }

        // Active output
        val localActive = state.activeOutput == "This device"
        Box(
            Modifier
                .fillMaxWidth()
                .border(1.dp, if (localActive) ActiveGreen else Color.White.copy(0.15f), RoundedCornerShape(12.dp))
                .background(Color.White.copy(0.04f), RoundedCornerShape(12.dp))
                .clickable {
                    vm.disconnectRemote()
                    vm.openConnect(false)
                }
                .padding(14.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Default.PhoneAndroid,
                    contentDescription = null,
                    tint = if (localActive) ActiveGreen else Color.White,
                )
                Spacer(Modifier.size(12.dp))
                Column {
                    Text(
                        "This device",
                        color = if (localActive) ActiveGreen else Color.White,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text("Play audio & video stored on this phone / headset", color = Color.White.copy(0.55f), style = MaterialTheme.typography.bodySmall)
                }
            }
        }

        Text("Select a device", fontWeight = FontWeight.Medium)
        if (state.scanning) {
            Text("Looking on Wi‑Fi…", color = Color.White.copy(0.55f))
        } else if (state.discovered.isEmpty()) {
            Text("No other devices found", color = Color.White.copy(0.55f))
            TipRow(Icons.Default.Wifi, "Check your Wi‑Fi", "Connect this device and the PC to the same network (use voxplayer-lan-bypass if a VPN hides LAN).")
            TipRow(Icons.Default.Computer, "Start VoxPlayer on the PC", "Desktop must be running with LAN daemon enabled; it will appear automatically.")
            TipRow(Icons.Default.Bluetooth, "Bluetooth", "Paired BT devices are listed as hints. Control uses Wi‑Fi once both share a LAN — enable Bluetooth to confirm nearby PCs.")
        } else {
            state.discovered.forEach { d ->
                val selected = state.activeOutput.contains(d.host)
                Box(
                    Modifier
                        .fillMaxWidth()
                        .border(1.dp, if (selected) ActiveGreen else Color.White.copy(0.12f), RoundedCornerShape(12.dp))
                        .clickable { vm.connectDesktop(d.host, d.port) }
                        .padding(14.dp),
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Computer, null, tint = if (selected) ActiveGreen else Color.White)
                        Spacer(Modifier.size(12.dp))
                        Column {
                            Text(d.name, color = if (selected) ActiveGreen else Color.White, fontWeight = FontWeight.SemiBold)
                            Text("${d.host}:${d.port} · Wi‑Fi · v${d.version.ifBlank { "?" }}", color = Color.White.copy(0.55f), style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }

        if (state.bondedHints.isNotEmpty()) {
            Text("Bluetooth paired nearby", fontWeight = FontWeight.Medium)
            state.bondedHints.forEach { name ->
                Text("· $name", color = Color.White.copy(0.55f), style = MaterialTheme.typography.bodySmall)
            }
            Text(
                "After pairing, join the same Wi‑Fi as the PC and tap Refresh — discovery is over Wi‑Fi for GrapheneOS (no Google Nearby).",
                color = Color.White.copy(0.45f),
                style = MaterialTheme.typography.bodySmall,
            )
        }

        OutlinedTextField(
            value = state.remoteHost,
            onValueChange = vm::updateRemoteHost,
            label = { Text("Desktop host (manual)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        OutlinedTextField(
            value = state.remotePort,
            onValueChange = vm::updateRemotePort,
            label = { Text("Port") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { vm.scanDesktops() }) {
                Icon(Icons.Default.Refresh, null)
                Spacer(Modifier.size(6.dp))
                Text("Refresh")
            }
            Button(onClick = { vm.connectManual() }) { Text("Connect") }
            TextButton(onClick = { vm.disconnectRemote(); vm.openConnect(false) }) { Text("This device") }
        }
    }
}

@Composable
private fun TipRow(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, body: String) {
    Row(Modifier.padding(vertical = 6.dp)) {
        Icon(icon, null, modifier = Modifier.padding(top = 2.dp))
        Spacer(Modifier.size(12.dp))
        Column {
            Text(title, fontWeight = FontWeight.Medium)
            Text(body, color = Color.White.copy(0.55f), style = MaterialTheme.typography.bodySmall)
        }
    }
}
