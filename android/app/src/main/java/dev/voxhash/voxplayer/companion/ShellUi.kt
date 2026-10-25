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
import androidx.compose.foundation.gestures.detectVerticalDragGestures
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
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.rememberCoroutineScope
import kotlinx.coroutines.launch
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.DragHandle
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
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.layout.positionInParent
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.zIndex
import kotlin.math.roundToInt
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

    val importM3u = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri != null) vm.importM3u(uri)
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

    val windowLayout = rememberWindowLayoutState()
    LaunchedEffect(windowLayout.foldSeparating, windowLayout.multiWindow) {
        vm.updateFoldLayout(windowLayout.foldSeparating)
        vm.onWindowLayoutChanged(
            multiWindow = windowLayout.multiWindow,
            orientation = context.resources.configuration.orientation,
        )
    }

    BoxWithConstraints(Modifier.fillMaxSize().background(VoxColors.BgApp)) {
        val wide = maxWidth >= WIDE_SHELL_MIN_DP.dp
        // Quest short panel / multi-window strip: keep transport usable, skip tall chrome.
        val panelCompact = maxHeight < PANEL_COMPACT_MAX_HEIGHT_DP.dp ||
            windowLayout.multiWindow && maxHeight < 640.dp
        // Driving layout only when tall enough — never in a short Quest panel / split.
        val carMode = !panelCompact &&
            maxWidth >= CAR_SHELL_MIN_DP.dp &&
            maxWidth > maxHeight * 1.15f
        val foldPad = if (windowLayout.foldSeparating) 28.dp else 0.dp
        Scaffold(
            containerColor = VoxColors.BgApp,
            bottomBar = {
                if (!carMode) TransportBar(
                    state = state,
                    wide = wide && !panelCompact,
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
                    .padding(pad)
                    .padding(horizontal = foldPad),
            ) {
                if (!panelCompact) {
                    LeftRail(
                        state = state,
                        onHome = { vm.setTab(AppTab.Local) },
                        onDesktop = { vm.setTab(AppTab.Connect) },
                        onOpen = { openDoc.launch(arrayOf("audio/*", "video/*")) },
                        onConnect = { vm.openConnect(true) },
                    )
                }
                Column(Modifier.weight(1f).fillMaxHeight()) {
                    if (!carMode && !panelCompact) {
                        ShellHeader(
                            state = state,
                            wide = wide,
                            onCycleTheme = vm::cycleThemeMode,
                        )
                    }
                    if (panelCompact) {
                        CompactPanelChrome(
                            state = state,
                            onHome = { vm.setTab(AppTab.Local) },
                            onDesktop = { vm.setTab(AppTab.Connect) },
                            onConnect = { vm.openConnect(true) },
                        )
                    }
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
                                    onImportM3u = {
                                        importM3u.launch(
                                            arrayOf(
                                                "audio/x-mpegurl",
                                                "application/vnd.apple.mpegurl",
                                                "audio/mpegurl",
                                                "text/plain",
                                                "*/*",
                                            ),
                                        )
                                    },
                                    onExportPlaylistM3u = { id -> vm.exportPlaylistM3u(context, id) },
                                    onFilter = vm::setLocalFilter,
                                    onSearch = vm::setLocalSearchQuery,
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
                        if (wide && !carMode && !panelCompact) {
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
                                onFadeMs = vm::setFadeMs,
                                onPlaybackSpeed = vm::setPlaybackSpeed,
                                onToggleDlna = { vm.setDlnaEnabled(!state.dlnaEnabled) },
                                onScanDlna = vm::scanDlnaRenderers,
                                onSelectDlna = vm::selectDlnaRenderer,
                                onCastDlna = vm::castNowPlayingToDlna,
                                onDlnaPlay = vm::dlnaPlay,
                                onDlnaPause = vm::dlnaPause,
                                onDlnaStop = vm::dlnaStop,
                                onShareNowPlaying = { vm.shareNowPlayingCard(context) },
                                onExportQueueM3u = { vm.exportQueueM3u(context) },
                                onBookmarkNow = vm::bookmarkNow,
                                onPlayBookmark = vm::playBookmark,
                                onRemoveBookmark = vm::removeBookmark,
                                onClearBookmarks = vm::clearBookmarks,
                                onClearTrackResume = vm::clearTrackResume,
                                onSeekLocal = vm::seekLocal,
                                onPlayQueueIndex = vm::playQueueIndex,
                                onMoveQueue = vm::moveQueueItem,
                                onRemoveQueue = vm::removeQueueItem,
                                onClearQueue = vm::requestClearLocalQueue,
                                onCancelClearQueue = vm::cancelClearLocalQueue,
                                onUndoClearQueue = vm::undoLastQueueChange,
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
private fun CompactPanelChrome(
    state: PlayerUiState,
    onHome: () -> Unit,
    onDesktop: () -> Unit,
    onConnect: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .background(VoxColors.BgPanel)
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("VX", color = VoxColors.Accent, fontWeight = FontWeight.Bold, fontSize = 13.sp)
        QuietButton(
            if (state.tab == AppTab.Local) "· Home" else "Home",
            onHome,
        )
        QuietButton(
            if (state.tab == AppTab.Connect) "· Desktop" else "Desktop",
            onDesktop,
        )
        Spacer(Modifier.weight(1f))
        Text(
            when {
                state.multiWindow -> "Split"
                state.foldSeparating -> "Fold"
                else -> "Panel"
            },
            style = MaterialTheme.typography.labelSmall,
            color = VoxColors.TextMuted,
        )
        QuietButton("Connect", onConnect)
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
private fun ShellHeader(
    state: PlayerUiState,
    wide: Boolean,
    onCycleTheme: () -> Unit,
) {
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
            Column(Modifier.weight(1f)) {
                Text("VoxPlayer", style = MaterialTheme.typography.headlineMedium, color = VoxColors.Accent)
                Text(
                    if (wide) "Library · Now Playing · Connect" else "On-device library & desktop remote",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            QuietButton(
                "Theme · ${state.themeMode.label()}",
                onCycleTheme,
            )
            Text(
                state.activeOutput,
                color = if (state.activeOutput.startsWith("Desktop")) VoxColors.Success else VoxColors.TextMuted,
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier.padding(start = 8.dp),
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
    onImportM3u: () -> Unit,
    onExportPlaylistM3u: (String) -> Unit,
    onFilter: (String) -> Unit,
    onSearch: (String) -> Unit,
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
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(
                Modifier.weight(1f).horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                listOf(
                    "all" to "All",
                    "audio" to "Audio",
                    "video" to "Video",
                    "recent" to "Recent",
                    "top" to "Top",
                    "week" to "Week",
                    "month" to "Month",
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
            }
            QuietButton("Open", onOpenFile)
        }

        if (state.localFilter != "lists") {
            OutlinedTextField(
                value = state.localSearchQuery,
                onValueChange = onSearch,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
                singleLine = true,
                label = { Text("Search title, artist, album") },
                trailingIcon = {
                    if (state.localSearchQuery.isNotEmpty()) {
                        IconButton(onClick = { onSearch("") }) {
                            Icon(
                                Icons.Default.Close,
                                contentDescription = "Clear search",
                                tint = VoxColors.TextMuted,
                            )
                        }
                    }
                },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = VoxColors.Accent,
                    unfocusedBorderColor = VoxColors.BorderSoft,
                    focusedLabelColor = VoxColors.Accent,
                    cursorColor = VoxColors.Accent,
                    focusedTextColor = VoxColors.Text,
                    unfocusedTextColor = VoxColors.Text,
                ),
            )
        }

        val historyFacet = state.localFilter == "recent" || state.localFilter == "top" ||
            state.localFilter == "week" || state.localFilter == "month"
        val periodFacet = state.localFilter == "week" || state.localFilter == "month"
        val listsFacet = state.localFilter == "lists"
        val q = state.localSearchQuery.trim()
        val periodStats = when (state.localFilter) {
            "week" -> state.historyWeek
            "month" -> state.historyMonth
            else -> null
        }
        val historyRows = remember(
            state.historyRecent,
            state.historyTop,
            state.historyWeek,
            state.historyMonth,
            state.localFilter,
            q,
        ) {
            val base = when (state.localFilter) {
                "recent" -> state.historyRecent
                "top" -> state.historyTop
                "week" -> state.historyWeek.tracks
                "month" -> state.historyMonth.tracks
                else -> emptyList()
            }
            if (q.isEmpty()) base
            else {
                val needle = q.lowercase()
                base.filter {
                    it.title.lowercase().contains(needle) ||
                        it.artist.lowercase().contains(needle) ||
                        it.album.lowercase().contains(needle)
                }
            }
        }
        val filtered = remember(state.localItems, state.localFilter, q) {
            val base = when (state.localFilter) {
                "audio" -> state.localItems.filter { !it.isVideo }
                "video" -> state.localItems.filter { it.isVideo }
                "recent", "top", "week", "month", "lists" -> emptyList()
                else -> state.localItems
            }
            if (q.isEmpty()) base
            else {
                val needle = q.lowercase()
                base.filter {
                    it.title.lowercase().contains(needle) ||
                        it.artist.lowercase().contains(needle) ||
                        it.album.lowercase().contains(needle)
                }
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
                    state.localFilter == "week" -> "This week · ${historyRows.size}"
                    state.localFilter == "month" -> "This month · ${historyRows.size}"
                    listsFacet && state.listsBrowseId != null -> "List"
                    listsFacet -> "Lists · ${state.localPlaylists.size} folders"
                    else -> "Home · ${filtered.size} items"
                },
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.weight(1f),
            )
            if (historyFacet && (
                    state.historyRecent.isNotEmpty() ||
                        state.historyTop.isNotEmpty() ||
                        state.historyWeek.listenCount > 0 ||
                        state.historyMonth.listenCount > 0
                    )
            ) {
                QuietButton("Clear history", onClearHistory)
            }
            if (listsFacet && state.listsBrowseId == null) {
                QuietButton("Import M3U", onImportM3u)
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
                onExportPlaylistM3u = onExportPlaylistM3u,
                modifier = Modifier.weight(1f).fillMaxWidth(),
            )
            return
        }

        if (periodFacet && periodStats != null) {
            val summary = buildString {
                append("${periodStats.listenCount} listens · ${periodStats.uniqueTracks} tracks")
                if (periodStats.topArtist.isNotBlank()) {
                    append(" · Top artist: ${periodStats.topArtist}")
                }
            }
            Text(
                summary,
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextSecondary,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 8.dp),
            )
        }

        val cols = if (wide) 4 else 2
        if (historyFacet) {
            if (historyRows.isEmpty()) {
                LibraryEmptyTips(
                    filter = state.localFilter,
                    searchActive = q.isNotEmpty(),
                    onOpenFile = onOpenFile,
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .padding(vertical = 24.dp),
                )
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(cols),
                    contentPadding = PaddingValues(bottom = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxSize(),
                ) {
                    items(historyRows, key = { "h-${it.uri}" }) { entry ->
                        HistoryCard(entry = entry, facet = state.localFilter, onClick = { onPlayHistory(entry) })
                    }
                }
            }
        } else if (filtered.isEmpty()) {
            LibraryEmptyTips(
                filter = state.localFilter,
                searchActive = q.isNotEmpty(),
                libraryTotal = state.localItems.size,
                onOpenFile = onOpenFile,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(vertical = 24.dp),
            )
        } else {
            AzLibraryGrid(
                items = filtered,
                cols = cols,
                onPlay = onPlay,
                modifier = Modifier.fillMaxSize(),
            )
        }
    }
}

@Composable
private fun LibraryEmptyTips(
    filter: String,
    searchActive: Boolean,
    onOpenFile: () -> Unit,
    modifier: Modifier = Modifier,
    libraryTotal: Int = 0,
) {
    val (headline, body) = when {
        searchActive -> "No matches" to "Try a shorter search, or clear the search field to see the full library."
        filter == "recent" -> "No recent plays yet" to "Play something from Home or Open a file — Recently played fills in on this device only (no cloud)."
        filter == "top" -> "No play counts yet" to "Most played builds from on-device listens. Keep playing tracks from your library to rank them here."
        filter == "week" -> "Quiet week so far" to "Week stats use local listen events from the last 7 days. Nothing has been counted yet."
        filter == "month" -> "Quiet month so far" to "Month stats use local listen events from the last 30 days. Play tracks on-device to fill this view."
        filter == "audio" && libraryTotal > 0 -> "No audio in library" to "MediaStore found media, but nothing tagged as audio. Try All, or Open a file from storage / SAF."
        filter == "video" && libraryTotal > 0 -> "No video in library" to "MediaStore found media, but nothing tagged as video. Try All, or Open a file from storage / SAF."
        libraryTotal == 0 -> "Library is empty" to "Grant media access if prompted, or use Open to pick files via the system picker (GrapheneOS Storage Scopes friendly). No Google account required."
        else -> "Nothing here" to "Switch filters or Open a file. Playback stays on-device with Media3 — no GMS."
    }
    Column(
        modifier
            .clip(VoxShapes.panel)
            .background(VoxColors.BgElevated)
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(headline, style = MaterialTheme.typography.titleLarge, color = VoxColors.Accent)
        Text(body, style = MaterialTheme.typography.bodyMedium, color = VoxColors.TextSecondary)
        Text(
            "Tips: All / Audio / Video browse MediaStore · Recent / Top / Week / Month are local history · Lists for folders & M3U",
            style = MaterialTheme.typography.bodySmall,
            color = VoxColors.TextMuted,
        )
        QuietButton("Open file…", onOpenFile, Modifier.fillMaxWidth())
    }
}

private fun libraryIndexLetter(title: String): Char {
    val c = title.trim().firstOrNull()?.uppercaseChar()
    return if (c != null && c in 'A'..'Z') c else '#'
}

@Composable
private fun AzLibraryGrid(
    items: List<LocalMediaItem>,
    cols: Int,
    onPlay: (LocalMediaItem) -> Unit,
    modifier: Modifier = Modifier,
) {
    val sorted = remember(items) {
        items.sortedWith(
            compareBy(String.CASE_INSENSITIVE_ORDER) { it.title.ifBlank { it.uri.lastPathSegment.orEmpty() } },
        )
    }
    val grouped = remember(sorted) {
        sorted.groupBy { libraryIndexLetter(it.title.ifBlank { it.uri.lastPathSegment.orEmpty() }) }
            .toSortedMap(compareBy { if (it == '#') '@' else it })
    }
    val letters = remember(grouped) { grouped.keys.toList() }
    // Flat index: each section = 1 full-span header + N cells
    val letterStartIndex = remember(grouped) {
        var idx = 0
        buildMap {
            grouped.forEach { (letter, list) ->
                put(letter, idx)
                idx += 1 + list.size
            }
        }
    }
    val gridState = rememberLazyGridState()
    val scope = rememberCoroutineScope()

    Box(modifier) {
        LazyVerticalGrid(
            columns = GridCells.Fixed(cols),
            state = gridState,
            contentPadding = PaddingValues(bottom = 16.dp, end = if (letters.size > 1) 22.dp else 0.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.fillMaxSize(),
        ) {
            grouped.forEach { (letter, section) ->
                item(
                    key = "hdr-$letter",
                    span = { GridItemSpan(maxLineSpan) },
                ) {
                    Text(
                        letter.toString(),
                        Modifier
                            .fillMaxWidth()
                            .background(VoxColors.BgPanel)
                            .padding(vertical = 4.dp),
                        style = MaterialTheme.typography.titleSmall,
                        color = VoxColors.Accent,
                        fontWeight = FontWeight.Bold,
                    )
                }
                items(
                    items = section,
                    key = { "${it.isVideo}-${it.id}" },
                ) { item ->
                    MediaCard(item = item, onClick = { onPlay(item) })
                }
            }
        }
        if (letters.size > 1) {
            Column(
                Modifier
                    .align(Alignment.CenterEnd)
                    .padding(end = 2.dp)
                    .fillMaxHeight()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                letters.forEach { letter ->
                    Text(
                        letter.toString(),
                        Modifier
                            .clickable {
                                val target = letterStartIndex[letter] ?: return@clickable
                                scope.launch {
                                    gridState.animateScrollToItem(target)
                                }
                            }
                            .padding(horizontal = 4.dp, vertical = 1.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = VoxColors.TextMuted,
                        fontSize = 10.sp,
                    )
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
    onExportPlaylistM3u: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val browse = state.listsBrowseId
    if (browse == null) {
        Column(
            modifier.verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                "Import M3U creates a folder from local paths / MediaStore matches (no cloud).",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextSecondary,
            )
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
        if (isUser && tracks.isNotEmpty()) {
            QuietButton("Export M3U", { onExportPlaylistM3u(browse) }, Modifier.fillMaxWidth())
        }
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
            ArtworkThumb(
                contentUri = Uri.parse(entry.uri),
                isVideo = entry.isVideo,
                modifier = Modifier.fillMaxSize(),
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
            facet == "week" -> "${entry.playCount}× this week"
            facet == "month" -> "${entry.playCount}× this month"
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
            ArtworkThumb(
                contentUri = item.artworkContentUri(),
                isVideo = item.isVideo,
                modifier = Modifier.fillMaxSize(),
            )
            Text(
                if (item.isVideo) "VIDEO" else "AUDIO",
                color = VoxColors.TextMuted,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier
                    .align(Alignment.BottomStart)
                    .padding(8.dp)
                    .background(VoxColors.BgApp.copy(alpha = 0.55f))
                    .padding(horizontal = 6.dp, vertical = 2.dp),
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
    onFadeMs: (Long) -> Unit,
    onPlaybackSpeed: (Float) -> Unit,
    onToggleDlna: () -> Unit,
    onScanDlna: () -> Unit,
    onSelectDlna: (String) -> Unit,
    onCastDlna: () -> Unit,
    onDlnaPlay: () -> Unit,
    onDlnaPause: () -> Unit,
    onDlnaStop: () -> Unit,
    onShareNowPlaying: () -> Unit,
    onExportQueueM3u: () -> Unit,
    onBookmarkNow: () -> Unit,
    onPlayBookmark: (BookmarkStore.Bookmark) -> Unit,
    onRemoveBookmark: (String) -> Unit,
    onClearBookmarks: () -> Unit,
    onClearTrackResume: () -> Unit,
    onSeekLocal: (Long) -> Unit,
    onPlayQueueIndex: (Int) -> Unit,
    onMoveQueue: (Int, Int) -> Unit,
    onRemoveQueue: (Int) -> Unit,
    onClearQueue: () -> Unit,
    onCancelClearQueue: () -> Unit,
    onUndoClearQueue: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val desktop = state.activeOutput.startsWith("Desktop")
    val title = if (desktop) state.remoteTitle else state.localTitle
    val playing = if (desktop) state.remotePlaying else state.localPlaying
    val pos = if (desktop) state.remotePositionLabel else state.localPositionLabel
    val paneScroll = rememberScrollState()
    val paneScope = rememberCoroutineScope()
    val sectionY = remember { mutableStateMapOf<String, Int>() }
    val jumpToSection: (String) -> Unit = { id ->
        sectionY[id]?.let { y ->
            paneScope.launch { paneScroll.animateScrollTo(y.coerceAtLeast(0)) }
        }
    }
    val markSection: (String) -> Modifier = { id ->
        Modifier.onGloballyPositioned { coords ->
            sectionY[id] = coords.positionInParent().y.roundToInt()
        }
    }

    Column(
        modifier
            .verticalScroll(paneScroll)
            .padding(16.dp),
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
        if (!desktop && title != "(nothing loaded)") {
            PlaybackStatusChips(
                state = state,
                onChipClick = jumpToSection,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        if (!desktop && state.statusToast.isNotBlank()) {
            Text(
                state.statusToast,
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.Accent,
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(VoxShapes.card)
                    .background(VoxColors.AccentSoft)
                    .padding(horizontal = 10.dp, vertical = 6.dp),
            )
        }
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
        if (!desktop && title != "(nothing loaded)") {
            SeekScrubber(
                positionMs = state.localPositionMs,
                durationMs = state.localDurationMs,
                onSeek = onSeekLocal,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        if (!desktop && state.resumeHint.isNotBlank()) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    state.resumeHint,
                    style = MaterialTheme.typography.bodySmall,
                    color = VoxColors.Accent,
                    modifier = Modifier.weight(1f),
                )
                QuietButton("Forget", onClearTrackResume)
            }
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
            QuietButton("Share card", onShareNowPlaying, Modifier.fillMaxWidth())
            if (!desktop && state.localQueueSize > 0) {
                QuietButton("Export queue M3U", onExportQueueM3u, Modifier.fillMaxWidth())
            }
        }
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
                Modifier
                    .fillMaxWidth()
                    .then(markSection("transport")),
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
            Text(
                "Sound output",
                style = MaterialTheme.typography.titleMedium,
                color = VoxColors.Accent,
                modifier = markSection("out"),
            )
            Text(
                "Force a sink below, or use System default so Android picks (e.g. BT when connected).",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                QuietButton("Refresh sinks", onRefreshDevices)
            }
            val usingDefault = state.preferredAudioDeviceId == AudioRoute.DEFAULT_DEVICE_ID
            val selectedName = when {
                usingDefault -> "Routing: System default"
                else -> state.audioDevices.firstOrNull { it.id == state.preferredAudioDeviceId }
                    ?.let { "Routing: ${it.name} · ${it.typeLabel}" }
                    ?: "Routing: System default (preferred sink gone)"
            }
            Text(selectedName, style = MaterialTheme.typography.bodySmall, color = VoxColors.Accent)
            Text(
                if (usingDefault) "✓ System default" else "System default",
                Modifier
                    .fillMaxWidth()
                    .clip(VoxShapes.card)
                    .background(if (usingDefault) VoxColors.AccentSoft else VoxColors.BgElevated)
                    .clickable { onSelectDevice(AudioRoute.DEFAULT_DEVICE_ID) }
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                style = MaterialTheme.typography.bodyMedium,
                color = if (usingDefault) VoxColors.Accent else VoxColors.Text,
            )
            state.audioDevices.take(16).groupBy { it.routeGroup }.forEach { (group, devices) ->
                Text(
                    group,
                    style = MaterialTheme.typography.labelLarge,
                    color = VoxColors.TextMuted,
                    modifier = Modifier.padding(top = 6.dp, bottom = 2.dp),
                )
                devices.forEach { dev ->
                    val selected = state.preferredAudioDeviceId == dev.id
                    Text(
                        if (selected) "✓ ${dev.name} · ${dev.typeLabel}" else "${dev.name} · ${dev.typeLabel}",
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
            }
            Text(
                "Equalizer",
                style = MaterialTheme.typography.titleMedium,
                color = VoxColors.Accent,
                modifier = markSection("eq"),
            )
            EqualizerControl.PRESETS.chunked(3).forEach { row ->
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    row.forEach { (id, label) ->
                        val selected = state.eqPreset == id
                        Text(
                            if (selected) "✓ $label" else label,
                            Modifier
                                .weight(1f)
                                .clip(VoxShapes.card)
                                .background(if (selected) VoxColors.AccentSoft else VoxColors.BgElevated)
                                .clickable { onEqPreset(id) }
                                .padding(horizontal = 8.dp, vertical = 10.dp),
                            style = MaterialTheme.typography.bodyMedium,
                            color = if (selected) VoxColors.Accent else VoxColors.Text,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    repeat(3 - row.size) {
                        Spacer(Modifier.weight(1f))
                    }
                }
            }
            Text(
                EqualizerControl.describe(state.eqPreset),
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            Text(
                "Transitions",
                style = MaterialTheme.typography.titleMedium,
                color = VoxColors.Accent,
                modifier = markSection("transitions"),
            )
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
            if (state.crossfadeEnabled) {
                Text(
                    "Fade length · ${CrossfadeControl.fadeLabel(state.fadeMs)} (${state.fadeMs} ms)",
                    style = MaterialTheme.typography.bodySmall,
                    color = VoxColors.TextMuted,
                )
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    CrossfadeControl.FADE_OPTIONS.forEach { (ms, label) ->
                        val selected = state.fadeMs == ms
                        Text(
                            if (selected) "✓ $label" else label,
                            Modifier
                                .weight(1f)
                                .clip(VoxShapes.card)
                                .background(if (selected) VoxColors.AccentSoft else VoxColors.BgElevated)
                                .clickable { onFadeMs(ms) }
                                .padding(horizontal = 6.dp, vertical = 8.dp),
                            style = MaterialTheme.typography.bodySmall,
                            color = if (selected) VoxColors.Accent else VoxColors.Text,
                            maxLines = 1,
                        )
                    }
                }
            }
            Text(
                "Speed",
                style = MaterialTheme.typography.titleMedium,
                color = VoxColors.Accent,
                modifier = markSection("speed"),
            )
            Text(
                "Playback rate · ${PlaybackSpeed.label(state.playbackSpeed)} (podcasts / spoken word)",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            PlaybackSpeed.OPTIONS.chunked(3).forEach { row ->
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    row.forEach { (speed, label) ->
                        val selected = kotlin.math.abs(state.playbackSpeed - speed) < 0.001f
                        Text(
                            if (selected) "✓ $label" else label,
                            Modifier
                                .weight(1f)
                                .clip(VoxShapes.card)
                                .background(if (selected) VoxColors.AccentSoft else VoxColors.BgElevated)
                                .clickable { onPlaybackSpeed(speed) }
                                .padding(horizontal = 6.dp, vertical = 8.dp),
                            style = MaterialTheme.typography.bodySmall,
                            color = if (selected) VoxColors.Accent else VoxColors.Text,
                            maxLines = 1,
                        )
                    }
                    repeat(3 - row.size) { Spacer(Modifier.weight(1f)) }
                }
            }
            Text("DLNA cast", style = MaterialTheme.typography.titleMedium, color = VoxColors.Accent)
            Text(
                "LAN MediaRenderer only — no Google Cast / GMS",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            QuietButton(
                if (state.dlnaEnabled) "DLNA on" else "Enable DLNA",
                onToggleDlna,
                Modifier.fillMaxWidth(),
            )
            if (state.dlnaEnabled) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    QuietButton(
                        if (state.dlnaBusy) "…" else "Scan",
                        onScanDlna,
                        Modifier.weight(1f),
                    )
                    QuietButton("Cast now", onCastDlna, Modifier.weight(1f))
                }
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    QuietButton("Play", onDlnaPlay, Modifier.weight(1f))
                    QuietButton("Pause", onDlnaPause, Modifier.weight(1f))
                    QuietButton("Stop", onDlnaStop, Modifier.weight(1f))
                }
                state.dlnaRenderers.take(8).forEach { r ->
                    val selected = state.dlnaSelectedId == r.id
                    Text(
                        "${r.name}${if (r.isTv) " · TV" else ""} · ${r.address}",
                        Modifier
                            .fillMaxWidth()
                            .clip(VoxShapes.card)
                            .background(if (selected) VoxColors.AccentSoft else VoxColors.BgElevated)
                            .clickable { onSelectDlna(r.id) }
                            .padding(horizontal = 10.dp, vertical = 8.dp),
                        style = MaterialTheme.typography.bodySmall,
                        color = if (selected) VoxColors.Accent else VoxColors.Text,
                    )
                }
                if (state.dlnaMessage.isNotBlank()) {
                    Text(
                        state.dlnaMessage,
                        style = MaterialTheme.typography.bodySmall,
                        color = VoxColors.TextMuted,
                    )
                }
            }
            Text(
                "Sleep timer",
                style = MaterialTheme.typography.titleMedium,
                color = VoxColors.Accent,
                modifier = markSection("sleep"),
            )
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
            Text(
                "Manual pins. Last position is also remembered per track when you reopen it.",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
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
            if (state.localQueue.isNotEmpty() || state.queueUndoAvailable || state.queueItemUndoAvailable) {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .then(markSection("queue")),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        "Up next",
                        style = MaterialTheme.typography.titleMedium,
                        color = VoxColors.Accent,
                        modifier = Modifier.weight(1f),
                    )
                    if (state.queueUndoAvailable || state.queueItemUndoAvailable) {
                        QuietButton("Undo", onUndoClearQueue)
                    }
                    if (state.localQueue.isNotEmpty()) {
                        if (state.queueClearArmed) {
                            QuietButton("Cancel", onCancelClearQueue)
                            QuietButton("Confirm clear", onClearQueue)
                        } else {
                            QuietButton("Clear queue", onClearQueue)
                        }
                    }
                }
                if (state.localQueue.size > 1) {
                    val queueListState = rememberLazyListState()
                    val queueScope = rememberCoroutineScope()
                    val currentQueueIndex = state.localQueue.indexOfFirst { it.isCurrent }
                        .takeIf { it >= 0 }
                        ?: state.localQueueIndex.coerceIn(0, state.localQueue.lastIndex)
                    LaunchedEffect(currentQueueIndex, state.localQueue.size) {
                        if (currentQueueIndex in state.localQueue.indices) {
                            queueListState.animateScrollToItem(currentQueueIndex)
                        }
                    }
                    Row(
                        Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Text(
                            "Drag ≡ to reorder · arrows still work",
                            style = MaterialTheme.typography.bodySmall,
                            color = VoxColors.TextMuted,
                            modifier = Modifier.weight(1f),
                        )
                        QuietButton(
                            "Jump to playing",
                            {
                                queueScope.launch {
                                    if (currentQueueIndex in state.localQueue.indices) {
                                        queueListState.animateScrollToItem(currentQueueIndex)
                                    }
                                }
                            },
                        )
                    }
                    LazyColumn(
                        state = queueListState,
                        modifier = Modifier.weight(1f, fill = false).heightIn(max = 280.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        items(
                            state.localQueue,
                            key = { row -> row.uri.ifBlank { "${row.index}:${row.title}" } },
                        ) { row ->
                            QueueRowItem(
                                row = row,
                                queueSize = state.localQueue.size,
                                canMoveUp = row.index > 0,
                                canMoveDown = row.index < state.localQueue.lastIndex,
                                onPlay = { onPlayQueueIndex(row.index) },
                                onMove = onMoveQueue,
                                onMoveUp = { onMoveQueue(row.index, row.index - 1) },
                                onMoveDown = { onMoveQueue(row.index, row.index + 1) },
                                onRemove = { onRemoveQueue(row.index) },
                            )
                        }
                    }
                } else if (state.localQueue.size == 1) {
                    Text(
                        "1 item in queue",
                        style = MaterialTheme.typography.bodySmall,
                        color = VoxColors.TextMuted,
                    )
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
    queueSize: Int,
    canMoveUp: Boolean,
    canMoveDown: Boolean,
    onPlay: () -> Unit,
    onMove: (Int, Int) -> Unit,
    onMoveUp: () -> Unit,
    onMoveDown: () -> Unit,
    onRemove: () -> Unit,
) {
    val density = LocalDensity.current
    val haptics = LocalHapticFeedback.current
    val thresholdPx = with(density) { 48.dp.toPx() }
    var dragging by remember { mutableStateOf(false) }
    var dragOffsetY by remember { mutableFloatStateOf(0f) }
    var dragIndex by remember { mutableIntStateOf(row.index) }
    val positionLabel = "Queue item ${row.index + 1} of $queueSize"
    val titleLabel = row.title.ifBlank { "Untitled" }

    Row(
        Modifier
            .fillMaxWidth()
            .zIndex(if (dragging) 1f else 0f)
            .graphicsLayer {
                translationY = if (dragging) dragOffsetY else 0f
                shadowElevation = if (dragging) 8f else 0f
            }
            .clip(VoxShapes.card)
            .background(if (row.isCurrent) VoxColors.AccentSoft else VoxColors.BgElevated)
            .semantics(mergeDescendants = true) {
                contentDescription = buildString {
                    append(positionLabel)
                    append(", ")
                    append(titleLabel)
                    if (row.artist.isNotBlank()) {
                        append(" by ")
                        append(row.artist)
                    }
                    if (row.isCurrent) append(", now playing")
                    append(". Double-tap to play. Use drag handle or move buttons to reorder.")
                }
            }
            .clickable(enabled = !dragging, onClick = onPlay)
            .padding(horizontal = 4.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            Icons.Default.DragHandle,
            contentDescription = "Drag handle, reorder $titleLabel",
            tint = VoxColors.TextMuted,
            modifier = Modifier
                .size(36.dp)
                .pointerInput(queueSize) {
                    detectVerticalDragGestures(
                        onDragStart = {
                            haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                            dragging = true
                            dragIndex = row.index
                            dragOffsetY = 0f
                        },
                        onDragEnd = {
                            if (dragging) {
                                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                            }
                            dragging = false
                            dragOffsetY = 0f
                        },
                        onDragCancel = {
                            dragging = false
                            dragOffsetY = 0f
                        },
                        onVerticalDrag = { change, amount ->
                            change.consume()
                            dragOffsetY += amount
                            while (dragOffsetY <= -thresholdPx && dragIndex > 0) {
                                val from = dragIndex
                                onMove(from, from - 1)
                                dragIndex = from - 1
                                dragOffsetY += thresholdPx
                                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                            }
                            while (dragOffsetY >= thresholdPx && dragIndex < queueSize - 1) {
                                val from = dragIndex
                                onMove(from, from + 1)
                                dragIndex = from + 1
                                dragOffsetY -= thresholdPx
                                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                            }
                        },
                    )
                },
        )
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
        IconButton(
            onClick = onMoveUp,
            enabled = canMoveUp && !dragging,
            modifier = Modifier.size(36.dp),
        ) {
            Icon(
                Icons.Default.KeyboardArrowUp,
                contentDescription = "Move $titleLabel up in queue",
                tint = VoxColors.TextSecondary,
            )
        }
        IconButton(
            onClick = onMoveDown,
            enabled = canMoveDown && !dragging,
            modifier = Modifier.size(36.dp),
        ) {
            Icon(
                Icons.Default.KeyboardArrowDown,
                contentDescription = "Move $titleLabel down in queue",
                tint = VoxColors.TextSecondary,
            )
        }
        IconButton(
            onClick = onRemove,
            enabled = !dragging,
            modifier = Modifier.size(36.dp),
        ) {
            Icon(
                Icons.Default.Close,
                contentDescription = "Remove $titleLabel from queue",
                tint = VoxColors.TextMuted,
            )
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

private data class StatusChipSpec(
    val id: String,
    val label: String,
    val emphasize: Boolean,
)

@Composable
private fun PlaybackStatusChips(
    state: PlayerUiState,
    onChipClick: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val eqLabel = EqualizerControl.PRESETS.firstOrNull { it.first == state.eqPreset }?.second ?: "Off"
    val routeLabel = when {
        state.preferredAudioDeviceId == AudioRoute.DEFAULT_DEVICE_ID -> "Out: System"
        else -> {
            val dev = state.audioDevices.firstOrNull { it.id == state.preferredAudioDeviceId }
            if (dev != null) {
                val short = dev.name.trim().ifBlank { dev.typeLabel }.let { n ->
                    if (n.length > 18) n.take(17) + "…" else n
                }
                "Out: $short"
            } else {
                "Out: Unavailable"
            }
        }
    }
    val chips = buildList {
        if (state.localQueueSize > 0) {
            add(
                StatusChipSpec(
                    "queue",
                    "Queue ${state.localQueueIndex + 1}/${state.localQueueSize}",
                    emphasize = true,
                ),
            )
        }
        add(
            StatusChipSpec(
                "out",
                routeLabel,
                emphasize = state.preferredAudioDeviceId != AudioRoute.DEFAULT_DEVICE_ID,
            ),
        )
        if (state.sleepEndEpochMs > 0L && state.sleepRemainingLabel.isNotBlank() &&
            state.sleepRemainingLabel != "Off"
        ) {
            add(StatusChipSpec("sleep", "Sleep ${state.sleepRemainingLabel}", emphasize = true))
        }
        if (state.crossfadeEnabled) {
            add(
                StatusChipSpec(
                    "transitions",
                    "Fade ${CrossfadeControl.fadeLabel(state.fadeMs)}",
                    emphasize = false,
                ),
            )
        }
        if (state.skipSilence) {
            add(StatusChipSpec("transitions", "Skip silence", emphasize = false))
        }
        if (kotlin.math.abs(state.playbackSpeed - 1f) > 0.001f) {
            add(StatusChipSpec("speed", PlaybackSpeed.label(state.playbackSpeed), emphasize = false))
        }
        if (state.eqPreset != EqualizerControl.PRESET_OFF) {
            add(StatusChipSpec("eq", "EQ $eqLabel", emphasize = false))
        }
        if (state.localShuffle) {
            add(StatusChipSpec("transport", "Shuffle", emphasize = false))
        }
        when (state.localRepeatMode) {
            Media3Player.REPEAT_MODE_ONE ->
                add(StatusChipSpec("transport", "Repeat one", emphasize = false))
            Media3Player.REPEAT_MODE_ALL ->
                add(StatusChipSpec("transport", "Repeat all", emphasize = false))
        }
    }
    if (chips.isEmpty()) return
    Row(
        modifier
            .horizontalScroll(rememberScrollState())
            .semantics {
                contentDescription = chips.joinToString(", ") { it.label } +
                    ". Tap a chip to jump to its controls."
            },
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        chips.forEach { chip ->
            Text(
                chip.label,
                Modifier
                    .clip(VoxShapes.pill)
                    .background(if (chip.emphasize) VoxColors.AccentSoft else VoxColors.BgElevated)
                    .border(
                        1.dp,
                        if (chip.emphasize) VoxColors.Accent else VoxColors.BorderSoft,
                        VoxShapes.pill,
                    )
                    .clickable { onChipClick(chip.id) }
                    .padding(horizontal = 10.dp, vertical = 4.dp)
                    .semantics {
                        contentDescription = "${chip.label}. Jump to controls."
                    },
                style = MaterialTheme.typography.labelSmall,
                color = if (chip.emphasize) VoxColors.Accent else VoxColors.TextSecondary,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun SeekScrubber(
    positionMs: Long,
    durationMs: Long,
    onSeek: (Long) -> Unit,
    modifier: Modifier = Modifier,
) {
    val dur = durationMs.coerceAtLeast(0L)
    val enabled = dur > 0L
    var scrubbing by remember { mutableStateOf(false) }
    var scrubFrac by remember { mutableFloatStateOf(0f) }
    val liveFrac = if (dur > 0L) {
        (positionMs.toFloat() / dur.toFloat()).coerceIn(0f, 1f)
    } else {
        0f
    }
    val value = if (scrubbing) scrubFrac else liveFrac
    Column(modifier, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Slider(
            value = value,
            onValueChange = { v ->
                if (!enabled) return@Slider
                scrubbing = true
                scrubFrac = v
            },
            onValueChangeFinished = {
                if (!enabled) return@Slider
                val target = (scrubFrac * dur).toLong().coerceIn(0L, dur)
                onSeek(target)
                scrubbing = false
            },
            enabled = enabled,
            modifier = Modifier.fillMaxWidth(),
            colors = SliderDefaults.colors(
                thumbColor = VoxColors.Accent,
                activeTrackColor = VoxColors.Accent,
                inactiveTrackColor = VoxColors.BorderSoft,
                disabledThumbColor = VoxColors.TextMuted,
                disabledActiveTrackColor = VoxColors.BorderSoft,
                disabledInactiveTrackColor = VoxColors.BgHover,
            ),
        )
        if (scrubbing && enabled) {
            val preview = (scrubFrac * dur).toLong()
            Text(
                "Seek ${fmtMs(preview)}",
                style = MaterialTheme.typography.labelSmall,
                color = VoxColors.Accent,
            )
        }
    }
}

private fun fmtMs(ms: Long): String {
    val total = (ms / 1000L).coerceAtLeast(0L)
    val m = total / 60L
    val s = total % 60L
    return "%d:%02d".format(m, s)
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
