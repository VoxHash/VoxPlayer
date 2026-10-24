package dev.voxhash.voxplayer.companion

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.LibraryMusic
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Repeat
import androidx.compose.material.icons.filled.RepeatOne
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material.icons.filled.SkipNext
import androidx.compose.material.icons.filled.SkipPrevious
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.VolumeOff
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material.icons.filled.Wifi
import androidx.media3.common.Player as Media3Player
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.Player
import androidx.media3.ui.PlayerView

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VoxPlayerApp(vm: PlayerViewModel) {
    val state by vm.state.collectAsState()
    val player by vm.playerFlow.collectAsState()
    val context = LocalContext.current

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { vm.reloadLocalLibrary() }

    val btPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { vm.refreshBluetoothHints() }

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
        val mediaPerms = if (Build.VERSION.SDK_INT >= 33) {
            mutableListOf(
                Manifest.permission.READ_MEDIA_AUDIO,
                Manifest.permission.READ_MEDIA_VIDEO,
            )
        } else {
            mutableListOf(Manifest.permission.READ_EXTERNAL_STORAGE)
        }
        // Android 13+: media notification for background PlaybackService
        if (Build.VERSION.SDK_INT >= 33) {
            mediaPerms.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (vm.hasMediaPermission()) {
            vm.reloadLocalLibrary()
            if (Build.VERSION.SDK_INT >= 33) {
                permissionLauncher.launch(arrayOf(Manifest.permission.POST_NOTIFICATIONS))
            }
        } else {
            permissionLauncher.launch(mediaPerms.toTypedArray())
        }
    }

    BoxWithConstraints(Modifier.fillMaxSize().background(VoxColors.BgApp)) {
        val wide = maxWidth >= WIDE_SHELL_MIN_DP.dp
        val carMode = maxWidth >= CAR_SHELL_MIN_DP.dp && maxWidth > maxHeight * 1.15f
        Scaffold(
            containerColor = VoxColors.BgApp,
            bottomBar = {
                if (!carMode) TransportBar(
                    state = state,
                    wide = wide,
                    onConnect = { vm.openConnect(true) },
                    onPlayPause = {
                        if (state.activeOutput.startsWith("Desktop")) vm.remotePlayPause()
                        else vm.localPlayPause()
                    },
                    onPrev = {
                        if (state.activeOutput.startsWith("Desktop")) vm.remotePrev()
                        else vm.localPrev()
                    },
                    onNext = {
                        if (state.activeOutput.startsWith("Desktop")) vm.remoteNext()
                        else vm.localNext()
                    },
                    onStop = {
                        if (state.activeOutput.startsWith("Desktop")) vm.remoteStop()
                        else vm.localStop()
                    },
                    onShuffle = { if (!state.activeOutput.startsWith("Desktop")) vm.toggleLocalShuffle() },
                    onRepeat = { if (!state.activeOutput.startsWith("Desktop")) vm.cycleLocalRepeat() },
                    onVolDown = {
                        if (state.activeOutput.startsWith("Desktop")) vm.remoteVolDown()
                        else vm.localVolDown()
                    },
                    onVolUp = {
                        if (state.activeOutput.startsWith("Desktop")) vm.remoteVolUp()
                        else vm.localVolUp()
                    },
                    onMute = {
                        if (!state.activeOutput.startsWith("Desktop")) vm.toggleLocalMute()
                    },
                )
            },
        ) { pad ->
            Row(
                Modifier
                    .fillMaxSize()
                    .padding(pad),
            ) {
                LeftRail(
                    state = state,
                    onHome = { vm.setTab(AppTab.Local) },
                    onDesktop = { vm.setTab(AppTab.Connect) },
                    onOpen = { openDoc.launch(arrayOf("audio/*", "video/*")) },
                    onConnect = { vm.openConnect(true) },
                )
                Column(Modifier.weight(1f).fillMaxHeight()) {
                    if (!carMode) ShellHeader(state = state, wide = wide)
                    if (state.error.isNotBlank()) {
                        Text(
                            state.error,
                            color = VoxColors.Danger,
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.padding(horizontal = 20.dp, vertical = 4.dp),
                        )
                    }
                    if (carMode && state.tab == AppTab.Local) {
                        CarDrivingPane(
                            state = state,
                            onPlayPause = {
                                if (state.activeOutput.startsWith("Desktop")) vm.remotePlayPause()
                                else vm.localPlayPause()
                            },
                            onPrev = {
                                if (state.activeOutput.startsWith("Desktop")) vm.remotePrev()
                                else vm.localPrev()
                            },
                            onNext = {
                                if (state.activeOutput.startsWith("Desktop")) vm.remoteNext()
                                else vm.localNext()
                            },
                            onVolDown = vm::localVolDown,
                            onVolUp = vm::localVolUp,
                            onPlayHistory = vm::playHistory,
                            modifier = Modifier.weight(1f).fillMaxWidth(),
                        )
                    } else Row(Modifier.weight(1f).fillMaxWidth()) {
                        Box(Modifier.weight(1f).fillMaxHeight()) {
                            when (state.tab) {
                                AppTab.Local -> LocalLibraryPane(
                                    state = state,
                                    player = player,
                                    wide = wide,
                                    onPlay = vm::playLocal,
                                    onPlayHistory = vm::playHistory,
                                    onClearHistory = vm::clearPlayHistory,
                                    onOpenListsBrowse = vm::openListsBrowse,
                                    onCreatePlaylist = vm::createLocalPlaylist,
                                    onDeletePlaylist = vm::deleteLocalPlaylist,
                                    onPlaySmartList = vm::playSmartList,
                                    onPlayLocalPlaylist = { id -> vm.playLocalPlaylist(id) },
                                    onPlayListsTrack = vm::playListsBrowseTrack,
                                    onRemovePlaylistTrack = vm::removeFromLocalPlaylist,
                                    onAddNowPlayingTo = vm::addNowPlayingToPlaylist,
                                    onFilter = vm::setLocalFilter,
                                    onOpenFile = { openDoc.launch(arrayOf("audio/*", "video/*")) },
                                    onRequestPerm = {
                                        val perms = if (Build.VERSION.SDK_INT >= 33) {
                                            arrayOf(
                                                Manifest.permission.READ_MEDIA_AUDIO,
                                                Manifest.permission.READ_MEDIA_VIDEO,
                                            )
                                        } else {
                                            arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE)
                                        }
                                        permissionLauncher.launch(perms)
                                    },
                                )
                                AppTab.Connect -> DesktopRemotePane(state, vm, wide)
                            }
                        }
                        if (wide && !carMode) {
                            NowPlayingPane(
                                state = state,
                                player = player,
                                onPlayPause = {
                                    if (state.activeOutput.startsWith("Desktop")) vm.remotePlayPause()
                                    else vm.localPlayPause()
                                },
                                onShuffle = vm::toggleLocalShuffle,
                                onRepeat = vm::cycleLocalRepeat,
                                onVolDown = vm::localVolDown,
                                onVolUp = vm::localVolUp,
                                onMute = vm::toggleLocalMute,
                                onRefreshDevices = vm::refreshAudioDevices,
                                onSelectDevice = vm::setPreferredAudioDevice,
                                onEqPreset = vm::setEqPreset,
                                onSleepMinutes = vm::setSleepTimerMinutes,
                                onClearSleep = vm::clearSleepTimer,
                                onToggleCrossfade = { vm.setCrossfadeEnabled(!state.crossfadeEnabled) },
                                onToggleSkipSilence = { vm.setSkipSilence(!state.skipSilence) },
                                onBookmarkNow = vm::bookmarkNow,
                                onPlayBookmark = vm::playBookmark,
                                onRemoveBookmark = vm::removeBookmark,
                                onClearBookmarks = vm::clearBookmarks,
                                onPlayQueueIndex = vm::playQueueIndex,
                                onMoveQueue = vm::moveQueueItem,
                                onRemoveQueue = vm::removeQueueItem,
                                modifier = Modifier
                                    .width(300.dp)
                                    .fillMaxHeight()
                                    .background(VoxColors.BgPanel),
                            )
                        }
                    }
                }
            }
        }
    }

    if (state.connectOpen) {
        ModalBottomSheet(
            onDismissRequest = { vm.openConnect(false) },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            containerColor = VoxColors.BgElevated,
        ) {
            ConnectSheet(
                state = state,
                vm = vm,
                onNeedBluetoothPermission = {
                    if (Build.VERSION.SDK_INT >= 31) {
                        btPermissionLauncher.launch(
                            arrayOf(
                                Manifest.permission.BLUETOOTH_CONNECT,
                                Manifest.permission.BLUETOOTH_SCAN,
                            ),
                        )
                    }
                },
            )
        }
    }
}

@Composable
private fun CarDrivingPane(
    state: PlayerUiState,
    onPlayPause: () -> Unit,
    onPrev: () -> Unit,
    onNext: () -> Unit,
    onVolDown: () -> Unit,
    onVolUp: () -> Unit,
    onPlayHistory: (PlayHistoryStore.Entry) -> Unit,
    modifier: Modifier = Modifier,
) {
    val desktop = state.activeOutput.startsWith("Desktop")
    val title = if (desktop) state.remoteTitle else state.localTitle
    val artist = if (desktop) "" else state.localArtist
    val playing = if (desktop) state.remotePlaying else state.localPlaying
    val pos = if (desktop) state.remotePositionLabel else state.localPositionLabel

    Row(
        modifier
            .padding(horizontal = 28.dp, vertical = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(28.dp),
    ) {
        Column(
            Modifier.weight(1.4f).fillMaxHeight(),
            verticalArrangement = Arrangement.SpaceEvenly,
        ) {
            Text("Driving layout", style = MaterialTheme.typography.labelLarge, color = VoxColors.TextMuted)
            Text(
                title,
                style = MaterialTheme.typography.displaySmall,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                color = VoxColors.Text,
            )
            if (artist.isNotBlank()) {
                Text(
                    artist,
                    style = MaterialTheme.typography.headlineSmall,
                    color = VoxColors.TextSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Text(pos, style = MaterialTheme.typography.titleLarge, color = VoxColors.Accent)
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                AccentButton("Prev", onPrev, Modifier.weight(1f).height(72.dp))
                AccentButton(
                    if (playing) "Pause" else "Play",
                    onPlayPause,
                    Modifier.weight(1.4f).height(88.dp),
                )
                AccentButton("Next", onNext, Modifier.weight(1f).height(72.dp))
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                QuietButton("Vol −", onVolDown, Modifier.weight(1f).height(56.dp))
                QuietButton("Vol +", onVolUp, Modifier.weight(1f).height(56.dp))
            }
            Text(
                "No Google Auto — large landscape controls only",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
        }
        Column(
            Modifier.weight(1f).fillMaxHeight().verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("Recent", style = MaterialTheme.typography.titleLarge, color = VoxColors.Accent)
            if (state.historyRecent.isEmpty()) {
                Text(
                    "Play something to fill Recent",
                    style = MaterialTheme.typography.bodyMedium,
                    color = VoxColors.TextSecondary,
                )
            }
            state.historyRecent.take(8).forEach { entry ->
                Text(
                    entry.title,
                    Modifier
                        .fillMaxWidth()
                        .clip(VoxShapes.card)
                        .background(VoxColors.BgElevated)
                        .clickable { onPlayHistory(entry) }
                        .padding(horizontal = 16.dp, vertical = 18.dp),
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun LeftRail(
    state: PlayerUiState,
    onHome: () -> Unit,
    onDesktop: () -> Unit,
    onOpen: () -> Unit,
    onConnect: () -> Unit,
) {
    Column(
        Modifier
            .width(64.dp)
            .fillMaxHeight()
            .background(VoxColors.Rail)
            .padding(vertical = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Box(
            Modifier
                .size(40.dp)
                .clip(RoundedCornerShapeCompat)
                .background(VoxColors.AccentSoft),
            contentAlignment = Alignment.Center,
        ) {
            Text("VX", color = VoxColors.Accent, fontWeight = FontWeight.Bold, fontSize = 14.sp)
        }
        Spacer(Modifier.height(8.dp))
        RailBtn(Icons.Default.Home, "Home", state.tab == AppTab.Local, onHome)
        RailBtn(Icons.Default.Computer, "Desktop", state.tab == AppTab.Connect, onDesktop)
        RailBtn(Icons.Default.FolderOpen, "Open file", false, onOpen)
        Spacer(Modifier.weight(1f))
        RailBtn(
            Icons.Default.Devices,
            "Connect",
            state.activeOutput.startsWith("Desktop"),
            onConnect,
        )
    }
}

private val RoundedCornerShapeCompat = androidx.compose.foundation.shape.RoundedCornerShape(10.dp)

@Composable
private fun RailBtn(icon: ImageVector, tip: String, active: Boolean, onClick: () -> Unit) {
    Box(
        Modifier
            .size(44.dp)
            .clip(CircleShape)
            .background(if (active) VoxColors.AccentSoft else androidx.compose.ui.graphics.Color.Transparent)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            icon,
            contentDescription = tip,
            tint = if (active) VoxColors.Accent else VoxColors.TextSecondary,
            modifier = Modifier.size(22.dp),
        )
    }
}

@Composable
private fun ShellHeader(state: PlayerUiState, wide: Boolean) {
    Column(
        Modifier
            .fillMaxWidth()
            .background(
                Brush.verticalGradient(listOf(VoxColors.BgPanel, VoxColors.BgApp)),
            )
            .padding(horizontal = 20.dp, vertical = 14.dp),
    ) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column {
                Text("VoxPlayer", style = MaterialTheme.typography.headlineMedium, color = VoxColors.Accent)
                Text(
                    if (wide) "Library · Now Playing · Connect" else "On-device library & desktop remote",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            Text(
                state.activeOutput,
                color = if (state.activeOutput.startsWith("Desktop")) VoxColors.Success else VoxColors.TextMuted,
                style = MaterialTheme.typography.labelLarge,
            )
        }
    }
}

@Composable
private fun LocalLibraryPane(
    state: PlayerUiState,
    player: Player?,
    wide: Boolean,
    onPlay: (LocalMediaItem) -> Unit,
    onPlayHistory: (PlayHistoryStore.Entry) -> Unit,
    onClearHistory: () -> Unit,
    onOpenListsBrowse: (String?) -> Unit,
    onCreatePlaylist: () -> Unit,
    onDeletePlaylist: (String) -> Unit,
    onPlaySmartList: (String) -> Unit,
    onPlayLocalPlaylist: (String) -> Unit,
    onPlayListsTrack: (String) -> Unit,
    onRemovePlaylistTrack: (String, String) -> Unit,
    onAddNowPlayingTo: (String) -> Unit,
    onFilter: (String) -> Unit,
    onOpenFile: () -> Unit,
    onRequestPerm: () -> Unit,
) {
    if (state.permissionNeeded) {
        Column(
            Modifier.padding(28.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Allow access to music and videos", style = MaterialTheme.typography.headlineSmall)
            Text(
                "GrapheneOS: Storage Scopes or media permissions work. Open file uses the system picker without broad access.",
                style = MaterialTheme.typography.bodyMedium,
            )
            AccentButton("Grant media access", onRequestPerm)
            QuietButton("Open file…", onOpenFile)
        }
        return
    }

    Column(Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
        if (player != null && state.localIsVideo && (state.localPlaying || state.localTitle != "(nothing loaded)")) {
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
                    .aspectRatio(if (wide) 21f / 9f else 16f / 9f)
                    .clip(VoxShapes.art)
                    .background(androidx.compose.ui.graphics.Color.Black),
            )
            Spacer(Modifier.height(12.dp))
        }

        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            listOf(
                "all" to "All",
                "audio" to "Audio",
                "video" to "Video",
                "recent" to "Recent",
                "top" to "Top",
                "lists" to "Lists",
            ).forEach { (k, label) ->
                FilterChip(
                    selected = state.localFilter == k,
                    onClick = { onFilter(k) },
                    label = { Text(label) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = VoxColors.AccentSoft,
                        selectedLabelColor = VoxColors.Accent,
                        containerColor = VoxColors.BgElevated,
                        labelColor = VoxColors.TextSecondary,
                    ),
                    border = FilterChipDefaults.filterChipBorder(
                        enabled = true,
                        selected = state.localFilter == k,
                        borderColor = VoxColors.BorderSoft,
                        selectedBorderColor = VoxColors.Accent,
                    ),
                )
            }
            Spacer(Modifier.weight(1f))
            QuietButton("Open", onOpenFile)
        }

        val historyFacet = state.localFilter == "recent" || state.localFilter == "top"
        val listsFacet = state.localFilter == "lists"
        val historyRows = remember(state.historyRecent, state.historyTop, state.localFilter) {
            when (state.localFilter) {
                "recent" -> state.historyRecent
                "top" -> state.historyTop
                else -> emptyList()
            }
        }
        val filtered = remember(state.localItems, state.localFilter) {
            when (state.localFilter) {
                "audio" -> state.localItems.filter { !it.isVideo }
                "video" -> state.localItems.filter { it.isVideo }
                "recent", "top", "lists" -> emptyList()
                else -> state.localItems
            }
        }

        Row(
            Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                when {
                    state.localFilter == "recent" -> "Recently played · ${historyRows.size}"
                    state.localFilter == "top" -> "Most played · ${historyRows.size}"
                    listsFacet && state.listsBrowseId != null -> "List"
                    listsFacet -> "Lists · ${state.localPlaylists.size} folders"
                    else -> "Home · ${filtered.size} items"
                },
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.weight(1f),
            )
            if (historyFacet && (state.historyRecent.isNotEmpty() || state.historyTop.isNotEmpty())) {
                QuietButton("Clear history", onClearHistory)
            }
            if (listsFacet && state.listsBrowseId == null) {
                QuietButton("New list", onCreatePlaylist)
            }
            if (listsFacet && state.listsBrowseId != null) {
                QuietButton("Back", { onOpenListsBrowse(null) })
            }
        }

        if (listsFacet) {
            ListsPane(
                state = state,
                onOpenListsBrowse = onOpenListsBrowse,
                onDeletePlaylist = onDeletePlaylist,
                onPlaySmartList = onPlaySmartList,
                onPlayLocalPlaylist = onPlayLocalPlaylist,
                onPlayListsTrack = onPlayListsTrack,
                onRemovePlaylistTrack = onRemovePlaylistTrack,
                onAddNowPlayingTo = onAddNowPlayingTo,
                modifier = Modifier.weight(1f).fillMaxWidth(),
            )
            return
        }

        val cols = if (wide) 4 else 2
        LazyVerticalGrid(
            columns = GridCells.Fixed(cols),
            contentPadding = PaddingValues(bottom = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.fillMaxSize(),
        ) {
            if (historyFacet) {
                items(historyRows, key = { "h-${it.uri}" }) { entry ->
                    HistoryCard(entry = entry, facet = state.localFilter, onClick = { onPlayHistory(entry) })
                }
            } else {
                items(filtered, key = { "${it.isVideo}-${it.id}" }) { item ->
                    MediaCard(item = item, onClick = { onPlay(item) })
                }
            }
        }
    }
}

@Composable
private fun ListsPane(
    state: PlayerUiState,
    onOpenListsBrowse: (String?) -> Unit,
    onDeletePlaylist: (String) -> Unit,
    onPlaySmartList: (String) -> Unit,
    onPlayLocalPlaylist: (String) -> Unit,
    onPlayListsTrack: (String) -> Unit,
    onRemovePlaylistTrack: (String, String) -> Unit,
    onAddNowPlayingTo: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val browse = state.listsBrowseId
    if (browse == null) {
        Column(
            modifier.verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Smart lists", style = MaterialTheme.typography.labelLarge, color = VoxColors.TextMuted)
            listOf(
                LocalPlaylistStore.SMART_NEW to "New on device",
                LocalPlaylistStore.SMART_RECENT to "Recently played",
                LocalPlaylistStore.SMART_TOP to "Most played",
                LocalPlaylistStore.SMART_SHORT to "Short audio (≤3 min)",
            ).forEach { (id, label) ->
                ListFolderRow(
                    title = label,
                    subtitle = "Smart · tap to open",
                    onOpen = { onOpenListsBrowse(id) },
                    onPlay = { onPlaySmartList(id) },
                    onDelete = null,
                )
            }
            Text(
                "Your folders",
                style = MaterialTheme.typography.labelLarge,
                color = VoxColors.TextMuted,
                modifier = Modifier.padding(top = 8.dp),
            )
            if (state.localPlaylists.isEmpty()) {
                Text(
                    "No playlists yet — New list, then add Now Playing.",
                    style = MaterialTheme.typography.bodySmall,
                    color = VoxColors.TextSecondary,
                )
            }
            state.localPlaylists.forEach { pl ->
                ListFolderRow(
                    title = pl.name,
                    subtitle = "${pl.tracks.size} tracks",
                    onOpen = { onOpenListsBrowse(pl.id) },
                    onPlay = { onPlayLocalPlaylist(pl.id) },
                    onDelete = { onDeletePlaylist(pl.id) },
                )
            }
            Spacer(Modifier.height(24.dp))
        }
        return
    }

    val tracks: List<LocalPlaylistStore.Track> = when {
        browse == LocalPlaylistStore.SMART_NEW -> state.localItems.take(40).map {
            LocalPlaylistStore.Track(it.uri.toString(), it.title, it.artist, it.album, it.isVideo)
        }
        browse == LocalPlaylistStore.SMART_RECENT -> state.historyRecent.map {
            LocalPlaylistStore.Track(it.uri, it.title, it.artist, it.album, it.isVideo)
        }
        browse == LocalPlaylistStore.SMART_TOP -> state.historyTop.map {
            LocalPlaylistStore.Track(it.uri, it.title, it.artist, it.album, it.isVideo)
        }
        browse == LocalPlaylistStore.SMART_SHORT -> state.localItems
            .filter { !it.isVideo && it.durationMs in 1L..180_000L }
            .take(40)
            .map { LocalPlaylistStore.Track(it.uri.toString(), it.title, it.artist, it.album, it.isVideo) }
        else -> state.localPlaylists.find { it.id == browse }?.tracks.orEmpty()
    }
    val isUser = !browse.startsWith("smart:")
    val canAdd = isUser && state.localTitle != "(nothing loaded)"

    Column(modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        if (canAdd) {
            QuietButton("Add Now Playing", { onAddNowPlayingTo(browse) }, Modifier.fillMaxWidth())
        }
        if (tracks.isEmpty()) {
            Text(
                if (isUser) "Empty — play something, then Add Now Playing."
                else "Nothing in this smart list yet.",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextSecondary,
            )
        }
        tracks.forEach { t ->
            Row(
                Modifier
                    .fillMaxWidth()
                    .clip(VoxShapes.card)
                    .background(VoxColors.BgElevated)
                    .clickable { onPlayListsTrack(t.uri) }
                    .padding(horizontal = 12.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(t.title, style = MaterialTheme.typography.titleSmall, maxLines = 1)
                    Text(
                        t.artist.ifBlank { if (t.isVideo) "Video" else "Audio" },
                        style = MaterialTheme.typography.bodySmall,
                        color = VoxColors.TextSecondary,
                        maxLines = 1,
                    )
                }
                if (isUser) {
                    IconButton(onClick = { onRemovePlaylistTrack(browse, t.uri) }, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Default.Close, "Remove", tint = VoxColors.TextMuted)
                    }
                }
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun ListFolderRow(
    title: String,
    subtitle: String,
    onOpen: () -> Unit,
    onPlay: () -> Unit,
    onDelete: (() -> Unit)?,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(VoxShapes.card)
            .background(VoxColors.BgElevated)
            .clickable(onClick = onOpen)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = VoxColors.TextSecondary)
        }
        QuietButton("Play", onPlay)
        if (onDelete != null) {
            IconButton(onClick = onDelete, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Default.Close, "Delete list", tint = VoxColors.TextMuted)
            }
        }
    }
}

@Composable
private fun HistoryCard(
    entry: PlayHistoryStore.Entry,
    facet: String,
    onClick: () -> Unit,
) {
    Column(
        Modifier
            .clip(VoxShapes.card)
            .background(VoxColors.BgElevated)
            .clickable(onClick = onClick)
            .padding(10.dp),
    ) {
        Box(
            Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .clip(VoxShapes.art)
                .background(VoxColors.BgPanel),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                if (entry.isVideo) "Video" else "Audio",
                color = VoxColors.TextMuted,
                style = MaterialTheme.typography.labelMedium,
            )
        }
        Spacer(Modifier.height(8.dp))
        Text(
            entry.title,
            style = MaterialTheme.typography.titleSmall,
            maxLines = 2,
            color = VoxColors.Text,
        )
        val sub = when {
            facet == "top" -> "${entry.playCount}× played"
            entry.artist.isNotBlank() -> entry.artist
            else -> if (entry.isVideo) "Video" else "Audio"
        }
        Text(sub, style = MaterialTheme.typography.bodySmall, color = VoxColors.TextSecondary, maxLines = 1)
    }
}

@Composable
private fun MediaCard(item: LocalMediaItem, onClick: () -> Unit) {
    Column(
        Modifier
            .clip(VoxShapes.card)
            .background(VoxColors.BgElevated)
            .clickable(onClick = onClick)
            .padding(10.dp),
    ) {
        Box(
            Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .clip(VoxShapes.art)
                .background(
                    Brush.linearGradient(
                        listOf(VoxColors.BgHover, VoxColors.BgInput),
                    ),
                ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                if (item.isVideo) Icons.Default.PlayArrow else Icons.Default.LibraryMusic,
                contentDescription = null,
                tint = VoxColors.Accent,
                modifier = Modifier.size(36.dp),
            )
            Text(
                if (item.isVideo) "VIDEO" else "AUDIO",
                color = VoxColors.TextMuted,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier
                    .align(Alignment.BottomStart)
                    .padding(8.dp),
            )
        }
        Spacer(Modifier.height(8.dp))
        Text(
            item.title,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            style = MaterialTheme.typography.titleMedium,
        )
        if (item.artist.isNotBlank()) {
            Text(
                item.artist,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextSecondary,
            )
        }
        if (item.album.isNotBlank()) {
            Text(
                item.album,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
        }
    }
}

@Composable
private fun NowPlayingPane(
    state: PlayerUiState,
    player: Player?,
    onPlayPause: () -> Unit,
    onShuffle: () -> Unit,
    onRepeat: () -> Unit,
    onVolDown: () -> Unit,
    onVolUp: () -> Unit,
    onMute: () -> Unit,
    onRefreshDevices: () -> Unit,
    onSelectDevice: (Int) -> Unit,
    onEqPreset: (String) -> Unit,
    onSleepMinutes: (Int) -> Unit,
    onClearSleep: () -> Unit,
    onToggleCrossfade: () -> Unit,
    onToggleSkipSilence: () -> Unit,
    onBookmarkNow: () -> Unit,
    onPlayBookmark: (BookmarkStore.Bookmark) -> Unit,
    onRemoveBookmark: (String) -> Unit,
    onClearBookmarks: () -> Unit,
    onPlayQueueIndex: (Int) -> Unit,
    onMoveQueue: (Int, Int) -> Unit,
    onRemoveQueue: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val desktop = state.activeOutput.startsWith("Desktop")
    val title = if (desktop) state.remoteTitle else state.localTitle
    val playing = if (desktop) state.remotePlaying else state.localPlaying
    val pos = if (desktop) state.remotePositionLabel else state.localPositionLabel

    Column(
        modifier.padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text("Now playing", style = MaterialTheme.typography.titleMedium, color = VoxColors.Accent)
        Box(
            Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .clip(VoxShapes.panel)
                .background(VoxColors.BgElevated),
            contentAlignment = Alignment.Center,
        ) {
            if (player != null && !desktop && state.localIsVideo && title != "(nothing loaded)") {
                AndroidView(
                    factory = { ctx ->
                        PlayerView(ctx).apply {
                            this.player = player
                            useController = false
                        }
                    },
                    update = { it.player = player },
                    modifier = Modifier.fillMaxSize(),
                )
            } else {
                Text("VoxPlayer", color = VoxColors.Accent, fontWeight = FontWeight.Bold, fontSize = 22.sp)
            }
        }
        Text(title, style = MaterialTheme.typography.headlineSmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
        if (!desktop && state.localArtist.isNotBlank()) {
            Text(
                state.localArtist,
                style = MaterialTheme.typography.titleMedium,
                color = VoxColors.TextSecondary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        if (!desktop && state.localAlbum.isNotBlank()) {
            Text(
                state.localAlbum,
                style = MaterialTheme.typography.bodyMedium,
                color = VoxColors.TextMuted,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Text(pos, style = MaterialTheme.typography.bodySmall)
        if (!desktop && state.localQueueSize > 0) {
            Text(
                "Queue ${state.localQueueIndex + 1} / ${state.localQueueSize}" +
                    if (state.localShuffle) " · shuffle" else "",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
        }
        Text(
            if (playing) "Playing" else if (title == "(nothing loaded)" || title == "(desktop idle)") "Nothing playing" else "Paused",
            style = MaterialTheme.typography.bodyMedium,
        )
        AccentButton(
            if (playing) "Pause" else "Play",
            onPlayPause,
            modifier = Modifier.fillMaxWidth(),
        )
        if (!desktop) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                QuietButton("Vol −", onVolDown, Modifier.weight(1f))
                QuietButton(
                    if (state.localMuted) "Muted" else "Vol ${state.localVolume}%",
                    onMute,
                    Modifier.weight(1.2f),
                )
                QuietButton("Vol +", onVolUp, Modifier.weight(1f))
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                QuietButton(
                    if (state.localShuffle) "Shuffle on" else "Shuffle",
                    onShuffle,
                    Modifier.weight(1f),
                )
                QuietButton(
                    when (state.localRepeatMode) {
                        Media3Player.REPEAT_MODE_ONE -> "Repeat one"
                        Media3Player.REPEAT_MODE_ALL -> "Repeat all"
                        else -> "Repeat off"
                    },
                    onRepeat,
                    Modifier.weight(1f),
                )
            }
            Text("Sound output", style = MaterialTheme.typography.titleMedium, color = VoxColors.Accent)
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                QuietButton("Refresh", onRefreshDevices)
            }
            val selectedName = when {
                state.preferredAudioDeviceId == AudioRoute.DEFAULT_DEVICE_ID -> "System default"
                else -> state.audioDevices.firstOrNull { it.id == state.preferredAudioDeviceId }
                    ?.let { "${it.name} · ${it.typeLabel}" }
                    ?: "System default"
            }
            Text(selectedName, style = MaterialTheme.typography.bodySmall, color = VoxColors.TextMuted)
            QuietButton(
                "System default",
                { onSelectDevice(AudioRoute.DEFAULT_DEVICE_ID) },
                Modifier.fillMaxWidth(),
            )
            state.audioDevices.take(8).forEach { dev ->
                val selected = state.preferredAudioDeviceId == dev.id
                Text(
                    "${dev.name} · ${dev.typeLabel}",
                    Modifier
                        .fillMaxWidth()
                        .clip(VoxShapes.card)
                        .background(if (selected) VoxColors.AccentSoft else VoxColors.BgElevated)
                        .clickable { onSelectDevice(dev.id) }
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (selected) VoxColors.Accent else VoxColors.Text,
                )
            }
            Text("Equalizer", style = MaterialTheme.typography.titleMedium, color = VoxColors.Accent)
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                EqualizerControl.PRESETS.take(3).forEach { (id, label) ->
                    QuietButton(
                        label,
                        { onEqPreset(id) },
                        Modifier.weight(1f),
                    )
                }
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                EqualizerControl.PRESETS.drop(3).forEach { (id, label) ->
                    QuietButton(
                        if (state.eqPreset == id) "· $label" else label,
                        { onEqPreset(id) },
                        Modifier.weight(1f),
                    )
                }
            }
            Text(
                "EQ: ${EqualizerControl.PRESETS.firstOrNull { it.first == state.eqPreset }?.second ?: "Off"} · AOSP effect",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            Text("Transitions", style = MaterialTheme.typography.titleMedium, color = VoxColors.Accent)
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                QuietButton(
                    if (state.crossfadeEnabled) "Fade-in on" else "Fade-in off",
                    onToggleCrossfade,
                    Modifier.weight(1f),
                )
                QuietButton(
                    if (state.skipSilence) "Skip silence on" else "Skip silence",
                    onToggleSkipSilence,
                    Modifier.weight(1f),
                )
            }
            Text("Sleep timer", style = MaterialTheme.typography.titleMedium, color = VoxColors.Accent)
            Text(
                if (state.sleepEndEpochMs > 0L) "Ends in ${state.sleepRemainingLabel}" else "Off · fades then pauses",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                SleepTimer.DURATIONS_MIN.take(3).forEach { m ->
                    QuietButton("${m}m", { onSleepMinutes(m) }, Modifier.weight(1f))
                }
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                SleepTimer.DURATIONS_MIN.drop(3).forEach { m ->
                    QuietButton("${m}m", { onSleepMinutes(m) }, Modifier.weight(1f))
                }
                QuietButton("Off", onClearSleep, Modifier.weight(1f))
            }
            Text("Bookmarks", style = MaterialTheme.typography.titleMedium, color = VoxColors.Accent)
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                QuietButton("Save here", onBookmarkNow, Modifier.weight(1f))
                QuietButton("Clear all", onClearBookmarks, Modifier.weight(1f))
            }
            state.bookmarks.take(8).forEach { bm ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .clip(VoxShapes.card)
                        .background(VoxColors.BgElevated)
                        .clickable { onPlayBookmark(bm) }
                        .padding(horizontal = 10.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            bm.title,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Text(
                            fmtBookmarkPos(bm.positionMs),
                            style = MaterialTheme.typography.bodySmall,
                            color = VoxColors.TextMuted,
                        )
                    }
                    IconButton(onClick = { onRemoveBookmark(bm.uri) }, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Default.Close, "Remove bookmark", tint = VoxColors.TextMuted)
                    }
                }
            }
            Text("Lyrics", style = MaterialTheme.typography.titleMedium, color = VoxColors.Accent)
            if (state.lyricsLines.isEmpty()) {
                Text(
                    "No sidecar .lrc / .srt / .vtt / .txt next to this file",
                    style = MaterialTheme.typography.bodySmall,
                    color = VoxColors.TextMuted,
                )
            } else {
                Text(
                    "${state.lyricsSource}${if (state.lyricsTimed) " · timed" else " · plain"}",
                    style = MaterialTheme.typography.bodySmall,
                    color = VoxColors.TextMuted,
                )
                Column(
                    Modifier
                        .fillMaxWidth()
                        .heightIn(max = 200.dp)
                        .verticalScroll(rememberScrollState())
                        .clip(VoxShapes.card)
                        .background(VoxColors.BgElevated)
                        .padding(10.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    state.lyricsLines.forEachIndexed { i, line ->
                        val active = state.lyricsTimed && i == state.lyricsActiveIndex
                        Text(
                            line,
                            style = if (active) {
                                MaterialTheme.typography.titleSmall
                            } else {
                                MaterialTheme.typography.bodySmall
                            },
                            color = if (active) VoxColors.Accent else VoxColors.TextSecondary,
                        )
                    }
                }
            }
            if (state.localQueue.size > 1) {
                Text("Up next", style = MaterialTheme.typography.titleMedium, color = VoxColors.Accent)
                LazyColumn(
                    Modifier.weight(1f, fill = false).heightIn(max = 280.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    items(state.localQueue, key = { it.index to it.title }) { row ->
                        QueueRowItem(
                            row = row,
                            canMoveUp = row.index > 0,
                            canMoveDown = row.index < state.localQueue.lastIndex,
                            onPlay = { onPlayQueueIndex(row.index) },
                            onMoveUp = { onMoveQueue(row.index, row.index - 1) },
                            onMoveDown = { onMoveQueue(row.index, row.index + 1) },
                            onRemove = { onRemoveQueue(row.index) },
                        )
                    }
                }
            }
        }
        Text(
            "Engine: Media3 on-device · desktop via Wi‑Fi / Bluetooth",
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun QueueRowItem(
    row: QueueRow,
    canMoveUp: Boolean,
    canMoveDown: Boolean,
    onPlay: () -> Unit,
    onMoveUp: () -> Unit,
    onMoveDown: () -> Unit,
    onRemove: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(VoxShapes.card)
            .background(if (row.isCurrent) VoxColors.AccentSoft else VoxColors.BgElevated)
            .clickable(onClick = onPlay)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                row.title,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodyMedium,
                color = if (row.isCurrent) VoxColors.Accent else VoxColors.Text,
            )
            if (row.artist.isNotBlank()) {
                Text(
                    row.artist,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    style = MaterialTheme.typography.bodySmall,
                    color = VoxColors.TextMuted,
                )
            }
        }
        IconButton(onClick = onMoveUp, enabled = canMoveUp, modifier = Modifier.size(36.dp)) {
            Icon(Icons.Default.KeyboardArrowUp, "Move up", tint = VoxColors.TextSecondary)
        }
        IconButton(onClick = onMoveDown, enabled = canMoveDown, modifier = Modifier.size(36.dp)) {
            Icon(Icons.Default.KeyboardArrowDown, "Move down", tint = VoxColors.TextSecondary)
        }
        IconButton(onClick = onRemove, modifier = Modifier.size(36.dp)) {
            Icon(Icons.Default.Close, "Remove", tint = VoxColors.TextMuted)
        }
    }
}

@Composable
private fun DesktopRemotePane(state: PlayerUiState, vm: PlayerViewModel, wide: Boolean) {
    val linkLabel = when (state.remoteLink) {
        RemoteLink.Bluetooth -> "Bluetooth RFCOMM"
        RemoteLink.Wifi -> "Wi‑Fi"
        RemoteLink.None -> ""
    }
    Column(
        Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            if (state.remoteConnected) {
                "Connected · $linkLabel · desktop v${state.remoteVersion.ifBlank { "?" }}"
            } else {
                "Not connected — use Connect to find your PC"
            },
            color = if (state.remoteConnected) VoxColors.Success else VoxColors.Danger,
            style = MaterialTheme.typography.titleMedium,
        )
        Text(state.remoteTitle, style = MaterialTheme.typography.headlineSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text("${state.remotePositionLabel} · vol ${state.remoteVolume}%", style = MaterialTheme.typography.bodyMedium)

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            AccentButton("Prev", vm::remotePrev, Modifier.weight(1f))
            AccentButton(if (state.remotePlaying) "Pause" else "Play", vm::remotePlayPause, Modifier.weight(1f))
            AccentButton("Next", vm::remoteNext, Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            QuietButton("Stop", vm::remoteStop, Modifier.weight(1f))
            QuietButton("−5s", vm::remoteSeekBack, Modifier.weight(1f))
            QuietButton("+5s", vm::remoteSeekFwd, Modifier.weight(1f))
            QuietButton("Vol −", vm::remoteVolDown, Modifier.weight(1f))
            QuietButton("Vol +", vm::remoteVolUp, Modifier.weight(1f))
        }
        if (state.remoteConnected) {
            AccentButton(
                if (state.syncBusy) "Syncing…" else "Sync playlists & podcasts",
                vm::syncFromDesktop,
                Modifier.fillMaxWidth(),
                enabled = !state.syncBusy,
            )
        }
        if (state.syncMessage.isNotBlank()) {
            Text(state.syncMessage, style = MaterialTheme.typography.bodySmall)
        }

        LazyColumn(
            Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(6.dp),
            contentPadding = PaddingValues(bottom = 12.dp),
        ) {
            if (state.syncedPlaylists.isNotEmpty()) {
                item { Text("Synced playlists", style = MaterialTheme.typography.titleMedium) }
                state.syncedPlaylists.forEach { pl ->
                    item {
                        Text("${pl.name} (${pl.items.size})", color = VoxColors.TextSecondary)
                    }
                    items(pl.items.take(if (wide) 60 else 30)) { item ->
                        LibraryRow(item.title) { vm.remoteOpen(item.path) }
                    }
                }
            }
            if (state.syncedFeeds.isNotEmpty()) {
                item { Text("Synced podcasts", style = MaterialTheme.typography.titleMedium) }
                state.syncedFeeds.forEach { feed ->
                    item {
                        Text("${feed.title} (${feed.episodes.size})", color = VoxColors.TextSecondary)
                    }
                    items(feed.episodes.take(20)) { ep ->
                        LibraryRow(ep.title) { vm.playSyncedEpisode(ep) }
                    }
                }
            }
            item { Text("Desktop library", style = MaterialTheme.typography.titleMedium) }
            items(state.remoteLibrary.take(if (wide) 120 else 60)) { item ->
                LibraryRow(item.title) { vm.remoteOpen(item.path) }
            }
        }
    }
}

@Composable
private fun LibraryRow(title: String, onClick: () -> Unit) {
    Text(
        title,
        Modifier
            .fillMaxWidth()
            .clip(VoxShapes.card)
            .background(VoxColors.BgElevated)
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
        style = MaterialTheme.typography.bodyLarge,
    )
}

@Composable
private fun TransportBar(
    state: PlayerUiState,
    wide: Boolean,
    onConnect: () -> Unit,
    onPlayPause: () -> Unit,
    onPrev: () -> Unit,
    onNext: () -> Unit,
    onStop: () -> Unit,
    onShuffle: () -> Unit,
    onRepeat: () -> Unit,
    onVolDown: () -> Unit,
    onVolUp: () -> Unit,
    onMute: () -> Unit,
) {
    val playing = if (state.activeOutput.startsWith("Desktop")) state.remotePlaying else state.localPlaying
    val title = if (state.activeOutput.startsWith("Desktop")) state.remoteTitle else state.localTitle
    val pos = if (state.activeOutput.startsWith("Desktop")) state.remotePositionLabel else state.localPositionLabel
    val local = !state.activeOutput.startsWith("Desktop")
    val volLabel = if (local) {
        if (state.localMuted) "muted" else "vol ${state.localVolume}%"
    } else {
        "vol ${state.remoteVolume}%"
    }

    Row(
        Modifier
            .fillMaxWidth()
            .background(VoxColors.Transport)
            .border(width = 0.dp, color = VoxColors.BorderSoft)
            .padding(horizontal = 14.dp, vertical = if (wide) 12.dp else 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Box(
            Modifier
                .size(if (wide) 52.dp else 44.dp)
                .clip(VoxShapes.art)
                .background(VoxColors.BgElevated),
            contentAlignment = Alignment.Center,
        ) {
            Text("VX", color = VoxColors.Accent, fontWeight = FontWeight.Bold)
        }
        Column(Modifier.weight(1f)) {
            Text(title, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.titleMedium)
            val subtitle = buildString {
                if (local && state.localArtist.isNotBlank()) {
                    append(state.localArtist)
                    append(" · ")
                }
                append(pos)
                if (local && state.localQueueSize > 1) {
                    append(" · ")
                    append(state.localQueueIndex + 1)
                    append('/')
                    append(state.localQueueSize)
                }
                append(" · ")
                append(volLabel)
                append(" · ")
                append(state.activeOutput)
            }
            Text(subtitle, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
        }
        if (wide) {
            IconButton(onClick = onVolDown) {
                Icon(Icons.Default.VolumeOff, "Volume down", tint = VoxColors.TextSecondary, modifier = Modifier.size(20.dp))
            }
            Text(
                if (local && state.localMuted) "Mute" else if (local) "${state.localVolume}" else "${state.remoteVolume}",
                style = MaterialTheme.typography.labelLarge,
                color = if (local && state.localMuted) VoxColors.Accent else VoxColors.TextSecondary,
                modifier = Modifier.clickable(onClick = onMute),
            )
            IconButton(onClick = onVolUp) {
                Icon(Icons.Default.VolumeUp, "Volume up", tint = VoxColors.TextSecondary)
            }
        }
        if (wide && local) {
            IconButton(onClick = onShuffle) {
                Icon(
                    Icons.Default.Shuffle,
                    "Shuffle",
                    tint = if (state.localShuffle) VoxColors.Accent else VoxColors.TextSecondary,
                )
            }
            IconButton(onClick = onRepeat) {
                Icon(
                    if (state.localRepeatMode == Media3Player.REPEAT_MODE_ONE) {
                        Icons.Default.RepeatOne
                    } else {
                        Icons.Default.Repeat
                    },
                    "Repeat",
                    tint = if (state.localRepeatMode != Media3Player.REPEAT_MODE_OFF) {
                        VoxColors.Accent
                    } else {
                        VoxColors.TextSecondary
                    },
                )
            }
        }
        if (wide) {
            IconButton(onClick = onPrev) {
                Icon(Icons.Default.SkipPrevious, null, tint = VoxColors.Text)
            }
        }
        Box(
            Modifier
                .size(if (wide) 48.dp else 42.dp)
                .clip(CircleShape)
                .background(VoxColors.Accent)
                .clickable(onClick = onPlayPause),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                if (playing) Icons.Default.Pause else Icons.Default.PlayArrow,
                contentDescription = "Play/Pause",
                tint = VoxColors.BgApp,
                modifier = Modifier.size(26.dp),
            )
        }
        if (wide) {
            IconButton(onClick = onNext) {
                Icon(Icons.Default.SkipNext, null, tint = VoxColors.Text)
            }
            IconButton(onClick = onStop) {
                Icon(Icons.Default.Stop, null, tint = VoxColors.TextSecondary)
            }
        }
        Button(
            onClick = onConnect,
            colors = ButtonDefaults.buttonColors(
                containerColor = if (state.activeOutput.startsWith("Desktop")) VoxColors.Success else VoxColors.Accent,
                contentColor = VoxColors.BgApp,
            ),
            shape = VoxShapes.pill,
        ) {
            Icon(Icons.Default.Devices, null, modifier = Modifier.size(18.dp))
            Spacer(Modifier.size(6.dp))
            Text("Connect")
        }
    }
}

@Composable
private fun AccentButton(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.height(44.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = VoxColors.Accent,
            contentColor = VoxColors.BgApp,
            disabledContainerColor = VoxColors.BgHover,
        ),
        shape = VoxShapes.pill,
    ) { Text(label, fontWeight = FontWeight.SemiBold) }
}

@Composable
private fun QuietButton(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Button(
        onClick = onClick,
        modifier = modifier.height(44.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = VoxColors.BgElevated,
            contentColor = VoxColors.Text,
        ),
        shape = VoxShapes.pill,
    ) { Text(label) }
}

@Composable
private fun ConnectSheet(
    state: PlayerUiState,
    vm: PlayerViewModel,
    onNeedBluetoothPermission: () -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(start = 20.dp, end = 20.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Connect", style = MaterialTheme.typography.headlineSmall, color = VoxColors.Accent)
            IconButton(onClick = { vm.openConnect(false) }) {
                Icon(Icons.Default.Close, contentDescription = "Close", tint = VoxColors.TextSecondary)
            }
        }

        DevicePickRow(
            selected = state.activeOutput == "This device",
            icon = Icons.Default.PhoneAndroid,
            title = "This device",
            subtitle = "Play audio & video stored on this phone / headset",
            onClick = {
                vm.disconnectRemote()
                vm.openConnect(false)
            },
        )

        Text("Wi‑Fi desktops", style = MaterialTheme.typography.titleMedium)
        if (state.scanning) {
            Text("Looking on Wi‑Fi…", style = MaterialTheme.typography.bodyMedium)
        } else if (state.discovered.isEmpty()) {
            Text("No other devices found on Wi‑Fi", style = MaterialTheme.typography.bodyMedium)
            TipRow(Icons.Default.Wifi, "Check your Wi‑Fi", "Same LAN as the PC (use voxplayer-lan-bypass if a VPN hides LAN).")
            TipRow(Icons.Default.Computer, "Start VoxPlayer on the PC", "LAN daemon enabled — it appears automatically.")
            TipRow(Icons.Default.Bluetooth, "Or use Bluetooth", "Pair, then tap a device below for RFCOMM (no Google Nearby).")
        } else {
            state.discovered.forEach { d ->
                DevicePickRow(
                    selected = state.activeOutput.contains(d.host),
                    icon = Icons.Default.Computer,
                    title = d.name,
                    subtitle = "${d.host}:${d.port} · Wi‑Fi · v${d.version.ifBlank { "?" }}",
                    onClick = { vm.connectDesktop(d.host, d.port) },
                )
            }
        }

        Text("Bluetooth control", style = MaterialTheme.typography.titleMedium)
        if (!vm.hasBluetoothPermission() && Build.VERSION.SDK_INT >= 31) {
            TextButton(onClick = onNeedBluetoothPermission) { Text("Grant Bluetooth permission") }
        } else if (state.bondedDevices.isEmpty()) {
            Text(
                "No paired devices. Pair in system Bluetooth settings, then Refresh.",
                style = MaterialTheme.typography.bodyMedium,
            )
        } else {
            state.bondedDevices.forEach { d ->
                val selected = state.remoteLink == RemoteLink.Bluetooth &&
                    state.activeOutput.contains(d.name)
                DevicePickRow(
                    selected = selected,
                    icon = Icons.Default.Bluetooth,
                    title = d.name,
                    subtitle = "${d.address} · RFCOMM control",
                    onClick = { vm.connectBluetooth(d.address, d.name) },
                )
            }
        }

        val fieldColors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = VoxColors.Accent,
            unfocusedBorderColor = VoxColors.BorderSoft,
            focusedLabelColor = VoxColors.Accent,
            cursorColor = VoxColors.Accent,
            focusedTextColor = VoxColors.Text,
            unfocusedTextColor = VoxColors.Text,
        )
        OutlinedTextField(
            value = state.remoteHost,
            onValueChange = vm::updateRemoteHost,
            label = { Text("Desktop host (manual Wi‑Fi)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            colors = fieldColors,
        )
        OutlinedTextField(
            value = state.remotePort,
            onValueChange = vm::updateRemotePort,
            label = { Text("Port") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            colors = fieldColors,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            AccentButton("Refresh", {
                vm.scanDesktops()
                vm.refreshBluetoothHints()
            })
            QuietButton("Wi‑Fi", onClick = { vm.connectManual() })
            TextButton(onClick = { vm.disconnectRemote(); vm.openConnect(false) }) {
                Text("This device", color = VoxColors.TextSecondary)
            }
        }
    }
}

@Composable
private fun DevicePickRow(
    selected: Boolean,
    icon: ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(VoxShapes.card)
            .border(1.dp, if (selected) VoxColors.Accent else VoxColors.BorderSoft, VoxShapes.card)
            .background(if (selected) VoxColors.AccentSoft else VoxColors.BgPanel)
            .clickable(onClick = onClick)
            .padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, null, tint = if (selected) VoxColors.Accent else VoxColors.Text)
        Spacer(Modifier.size(12.dp))
        Column {
            Text(
                title,
                color = if (selected) VoxColors.Accent else VoxColors.Text,
                fontWeight = FontWeight.SemiBold,
            )
            Text(subtitle, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun TipRow(icon: ImageVector, title: String, body: String) {
    Row(Modifier.padding(vertical = 6.dp)) {
        Icon(icon, null, tint = VoxColors.Accent, modifier = Modifier.padding(top = 2.dp))
        Spacer(Modifier.size(12.dp))
        Column {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(body, style = MaterialTheme.typography.bodySmall)
        }
    }
}

private fun fmtBookmarkPos(ms: Long): String {
    val sec = (ms / 1000).coerceAtLeast(0)
    return "at %d:%02d".format(sec / 60, sec % 60)
}
