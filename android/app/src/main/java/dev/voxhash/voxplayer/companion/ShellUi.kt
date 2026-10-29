package dev.voxhash.voxplayer.companion

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
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
import androidx.compose.foundation.layout.widthIn
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.rememberCoroutineScope
import kotlinx.coroutines.launch
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material.icons.filled.AudioFile
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.Cast
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.DragHandle
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.Forward5
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.LibraryMusic
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Podcasts
import androidx.compose.material.icons.filled.Policy
import androidx.compose.material.icons.filled.QueueMusic
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Repeat
import androidx.compose.material.icons.filled.RepeatOne
import androidx.compose.material.icons.filled.Replay
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material.icons.filled.SkipNext
import androidx.compose.material.icons.filled.SkipPrevious
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.Timer
import androidx.compose.material.icons.filled.VolumeOff
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material.icons.filled.Wifi
import dev.voxhash.voxplayer.companion.BuildConfig
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
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
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.ui.graphics.graphicsLayer
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
import androidx.compose.runtime.snapshotFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
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

    val openBrowseTree = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocumentTree(),
    ) { uri: Uri? ->
        if (uri != null) {
            val label = uri.lastPathSegment
                ?.substringAfterLast(':')
                ?.replace("%2F", "/")
                ?.substringAfterLast('/')
                ?: "Folder"
            vm.addBrowseFavorite(uri, label)
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

    val windowLayout = rememberWindowLayoutState()
    LaunchedEffect(windowLayout.foldSeparating, windowLayout.multiWindow) {
        vm.updateFoldLayout(windowLayout.foldSeparating)
        vm.onWindowLayoutChanged(
            multiWindow = windowLayout.multiWindow,
            orientation = context.resources.configuration.orientation,
        )
    }

    val enterPip: () -> Unit = {
        (context.findActivity() as? MainActivity)?.enterPip()
    }

    // System PiP: video-only chrome so the OS window stays usable.
    if (state.pipActive) {
        Box(
            Modifier
                .fillMaxSize()
                .background(androidx.compose.ui.graphics.Color.Black),
            contentAlignment = Alignment.Center,
        ) {
            if (player != null && state.localIsVideo) {
                AndroidView(
                    factory = { ctx -> PlayerSurfaces.attachPlayerHost(ctx, player) },
                    update = { host -> host.bind(player) },
                    modifier = Modifier.fillMaxSize(),
                )
            } else {
                Text(
                    state.localTitle.ifBlank { "VoxPlayer" },
                    color = VoxColors.Accent,
                    style = MaterialTheme.typography.titleMedium,
                )
            }
        }
        return
    }

    BoxWithConstraints(Modifier.fillMaxSize().background(VoxColors.BgApp)) {
        val wide = maxWidth >= WIDE_SHELL_MIN_DP.dp
        // Quest short panel / multi-window strip: keep transport usable, skip tall chrome.
        val panelCompact = maxHeight < PANEL_COMPACT_MAX_HEIGHT_DP.dp ||
            windowLayout.multiWindow && maxHeight < 640.dp
        // Quest / split 2D panels (~1280×800): content-first like streaming + FOSS panel apps —
        // one rail, one mini-player, no stacked transport / header / side Now Playing.
        // Horizon OS often leaves Activity.isInMultiWindowMode=false while windowingMode is
        // multi-window, so also key off wide + short landscape height (h640dp / 800px).
        val panelLean = wide && !panelCompact && (
            windowLayout.multiWindow ||
                state.multiWindow ||
                (maxHeight <= 900.dp && maxWidth >= maxHeight)
            )
        // Driving layout only when tall enough — never in a short Quest panel / split.
        val carMode = !panelCompact &&
            !panelLean &&
            maxWidth >= CAR_SHELL_MIN_DP.dp &&
            maxWidth > maxHeight * 1.15f
        val foldPad = if (windowLayout.foldSeparating) 28.dp else 0.dp
        // Phone: bottom nav only. Tablet/wide: left rail only. Never both (FOSS player pattern).
        // Compact panel chrome already hosts destinations — don't stack a second bottom bar.
        val useRail = wide && !panelCompact
        val useBottomDest = !useRail && !carMode && !panelCompact
        val showShellHeader = !carMode && !panelCompact && !panelLean && !useRail
        val showSideNowPlaying = wide && !carMode && !panelCompact && !panelLean
        val showTransportBar = useRail && !panelLean
        LaunchedEffect(panelLean, useRail, showTransportBar, showSideNowPlaying, maxWidth, maxHeight) {
            Log.i(
                "VoxPlayerBT",
                "shell chrome lean=$panelLean rail=$useRail transport=$showTransportBar " +
                    "sideNp=$showSideNowPlaying header=$showShellHeader " +
                    "size=${maxWidth.value.toInt()}x${maxHeight.value.toInt()}dp",
            )
        }
        Scaffold(
            containerColor = VoxColors.BgApp,
            bottomBar = {
                if (!carMode) {
                    Column(Modifier.fillMaxWidth()) {
                        MiniPlayerBar(
                            state = state,
                            onPlayPause = {
                                if (state.activeOutput.startsWith("Desktop")) vm.remotePlayPause()
                                else vm.localPlayPause()
                            },
                            onOpenNowPlaying = vm::openNowPlayingTab,
                            onOpenSettings = { vm.openPlayerSheet(PlayerSheet.Settings) },
                            onShare = { vm.shareNowPlayingCard(context) },
                        )
                        if (useBottomDest) {
                            PrimaryDestBar(
                                selected = state.primaryDest(),
                                onSelect = vm::setPrimaryDest,
                            )
                        }
                        // Full transport only on non-panel wide shells — Quest lean uses mini + stage.
                        if (showTransportBar) {
                            TransportBar(
                                state = state,
                                wide = true,
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
                        }
                    }
                }
            },
        ) { pad ->
            Row(
                Modifier
                    .fillMaxSize()
                    .padding(pad)
                    .padding(horizontal = foldPad),
            ) {
                if (useRail) {
                    LeftRail(
                        state = state,
                        labeled = panelLean,
                        onSelectDest = vm::setPrimaryDest,
                        onOpen = { openDoc.launch(arrayOf("audio/*", "video/*")) },
                        onConnect = { vm.openConnect(true) },
                    )
                }
                Column(Modifier.weight(1f).fillMaxHeight()) {
                    if (showShellHeader) {
                        ShellHeader(
                            state = state,
                            wide = wide,
                            onConnect = { vm.openConnect(true) },
                        )
                    }
                    if (panelCompact) {
                        CompactPanelChrome(
                            state = state,
                            onSelectDest = vm::setPrimaryDest,
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
                                    railChrome = useRail,
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
                                    onAddListsTrackToList = { track ->
                                        val exclude = state.listsBrowseId
                                            ?.takeUnless { it.startsWith("smart:") }
                                        vm.openAddToListFromTrack(track, exclude)
                                    },
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
                                    onPinFilter = vm::setPreferredLocalFilter,
                                    onAudioFacet = vm::setAudioFacet,
                                    onPlayArtist = vm::playArtist,
                                    onPlayAlbum = vm::playAlbum,
                                    onBrowseShortcut = vm::openBrowseShortcut,
                                    onBrowseFavorite = vm::openBrowseFavorite,
                                    onBrowseInternal = vm::openBrowseInternalStorage,
                                    onBrowseBack = vm::closeBrowseFolder,
                                    onAddBrowseFolder = { openBrowseTree.launch(null) },
                                    onRemoveBrowseFavorite = vm::removeBrowseFavorite,
                                    onSearch = vm::setLocalSearchQuery,
                                    onHomeAzLetter = vm::setHomeAzLetter,
                                    onRefreshLibrary = vm::reloadLocalLibrary,
                                    onAddToList = vm::openAddToList,
                                    onAddHistoryToList = vm::openAddToListFromHistory,
                                    onSeekLocal = vm::seekLocal,
                                    onSetVolume = vm::setLocalVolume,
                                    onEnterPip = enterPip,
                                    onOpenPlayerSettings = { vm.openPlayerSheet(PlayerSheet.Settings) },
                                    onOpenCaptions = { vm.openPlayerSheet(PlayerSheet.Captions) },
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
                        if (showSideNowPlaying) {
                            NowPlayingPane(
                                state = state,
                                player = player,
                                onPlayPause = {
                                    if (state.activeOutput.startsWith("Desktop")) vm.remotePlayPause()
                                    else vm.localPlayPause()
                                },
                                onShuffle = vm::toggleLocalShuffle,
                                onPinShuffle = vm::setPreferredShuffleOn,
                                onRepeat = vm::cycleLocalRepeat,
                                onSetRepeat = vm::setLocalRepeatMode,
                                onPinRepeat = vm::setPreferredRepeatMode,
                                onVolDown = vm::localVolDown,
                                onVolUp = vm::localVolUp,
                                onMute = vm::toggleLocalMute,
                                onRefreshDevices = vm::refreshAudioDevices,
                                onSelectDevice = vm::setPreferredAudioDevice,
                                onPinDevice = vm::setPinnedAudioDevice,
                                onEqPreset = vm::setEqPreset,
                                onPinEqPreset = vm::setPreferredEqPreset,
                                onOpenEqSheet = { vm.openEqSheet(true) },
                                onSleepMinutes = vm::setSleepTimerMinutes,
                                onPinSleepMinutes = vm::setPreferredSleepMinutes,
                                onStartPreferredSleep = vm::startPreferredSleepTimer,
                                onClearSleep = vm::clearSleepTimer,
                                onToggleCrossfade = { vm.setCrossfadeEnabled(!state.crossfadeEnabled) },
                                onToggleSkipSilence = { vm.setSkipSilence(!state.skipSilence) },
                                onFadeMs = vm::setFadeMs,
                                onPinFadeMs = vm::setPreferredFadeMs,
                                onPlaybackSpeed = vm::setPlaybackSpeed,
                                onPinPlaybackSpeed = vm::setPreferredPlaybackSpeed,
                                onToggleDlna = { vm.setDlnaEnabled(!state.dlnaEnabled) },
                                onScanDlna = vm::scanDlnaRenderers,
                                onSelectDlna = vm::selectDlnaRenderer,
                                onSetDefaultDlna = vm::setDlnaDefaultRenderer,
                                onCastDlna = vm::castNowPlayingToDlna,
                                onDlnaPlay = vm::dlnaPlay,
                                onDlnaPause = vm::dlnaPause,
                                onDlnaStop = vm::dlnaStop,
                                onShareNowPlaying = { vm.shareNowPlayingCard(context) },
                                onExportQueueM3u = { vm.exportQueueM3u(context) },
                                onBookmarkNow = vm::bookmarkNow,
                                onPlayBookmark = vm::playBookmark,
                                onRemoveBookmark = vm::removeBookmark,
                                onAddBookmarkToList = vm::openAddToListFromBookmark,
                                onClearBookmarks = vm::clearBookmarks,
                                onClearPreferredPins = vm::clearAllPreferredPins,
                                onClearTrackResume = vm::clearTrackResume,
                                onSeekLocal = vm::seekLocal,
                                onSetVolume = vm::setLocalVolume,
                                onEnterPip = enterPip,
                                onPlayQueueIndex = vm::playQueueIndex,
                                onMoveQueue = vm::moveQueueItem,
                                onRemoveQueue = vm::removeQueueItem,
                                onAddQueueToList = vm::openAddToListFromQueueRow,
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

    ModernPlayerSheets(
        state = state,
        onDismiss = vm::dismissPlayerSheet,
        onOpenSheet = vm::openPlayerSheet,
        onSpeed = vm::setPlaybackSpeed,
        onNudgeSpeed = vm::nudgePlaybackSpeed,
        onCaptionsOff = { vm.setCaptionsMode(CaptionsMode.Off) },
        onCaptionsLyrics = { vm.setCaptionsMode(CaptionsMode.Lyrics) },
        onShowWhenMuted = vm::setCaptionsShowWhenMuted,
        onLoopVideo = vm::setLoopVideo,
        onAmbient = vm::setAmbientMode,
        onLockScreen = vm::setScreenLocked,
        onOpenSleep = { vm.openPlayerSheet(PlayerSheet.Sleep) },
        onQualityMode = vm::setQualityMode,
        onPlayNext = {
            vm.localNext()
            vm.dismissPlayerSheet()
        },
        onSavePlaylist = {
            vm.dismissPlayerSheet()
        },
        onShare = {
            vm.shareNowPlayingCard(context)
            vm.dismissPlayerSheet()
        },
        onAddQueue = {
            vm.openPlayerSheet(PlayerSheet.Queue)
        },
        onOpenStorage = { vm.openPlayerSheet(PlayerSheet.Storage) },
        onClearCache = vm::clearArtworkCache,
        onShowDeviceFiles = vm::setShowDeviceFiles,
        onPlayQueueIndex = { idx ->
            vm.playQueueIndex(idx)
            vm.dismissPlayerSheet()
        },
        onRemoveQueueIndex = vm::removeQueueItem,
        onPlayBookmark = { bm ->
            vm.playBookmark(bm)
            vm.dismissPlayerSheet()
            vm.openNowPlayingTab()
        },
        onRemoveBookmark = vm::removeBookmark,
        onBookmarkNow = vm::bookmarkNow,
        onSleepMinutes = vm::setSleepTimerMinutes,
        onClearSleep = vm::clearSleepTimer,
        onOpenDocs = {
            runCatching {
                context.startActivity(
                    Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/VoxHash/VoxPlayer#readme")),
                )
            }
        },
        onOpenReleases = {
            runCatching {
                context.startActivity(
                    Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/VoxHash/VoxPlayer/releases")),
                )
            }
        },
        appVersionLabel = BuildConfig.VERSION_NAME,
    )

    if (state.nowPlayingStage && !state.pipActive) {
        NowPlayingStage(
            state = state,
            player = player,
            audioSurface = state.stageAudioSurface,
            onDismiss = vm::dismissNowPlayingStage,
            onAudioSurface = vm::setStageAudioSurface,
            onPlayPause = vm::localPlayPause,
            onPrev = vm::localPrev,
            onNext = vm::localNext,
            onShuffle = vm::toggleLocalShuffle,
            onSeek = vm::seekLocal,
            onOpenCaptions = {
                vm.setCaptionsMode(CaptionsMode.Lyrics)
                vm.openPlayerSheet(PlayerSheet.Captions)
            },
            onOpenSettings = { vm.openPlayerSheet(PlayerSheet.Settings) },
            onShare = { vm.shareNowPlayingCard(context) },
            onSaveList = {
                val row = state.localQueue.firstOrNull { it.isCurrent }
                if (row != null && row.uri.isNotBlank()) {
                    vm.openAddToListFromQueueRow(row)
                }
            },
            onCast = vm::castFromNowPlaying,
            onBookmark = vm::bookmarkNow,
            onOpenQueue = { vm.openPlayerSheet(PlayerSheet.Queue) },
            onUnlock = { vm.setScreenLocked(false) },
            modifier = Modifier
                .fillMaxSize()
                .zIndex(8f),
        )
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

    val pendingAdd = state.addToListPending
    if (pendingAdd != null) {
        ModalBottomSheet(
            onDismissRequest = vm::dismissAddToList,
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            containerColor = VoxColors.BgElevated,
        ) {
            AddToListSheet(
                trackTitle = pendingAdd.title,
                playlists = state.localPlaylists.filter {
                    it.id != state.addToListExcludePlaylistId
                },
                onPick = vm::addPendingToPlaylist,
                onCreateNew = vm::createPlaylistAndAddPending,
                onDismiss = vm::dismissAddToList,
            )
        }
    }

    if (state.eqSheetOpen) {
        ModalBottomSheet(
            onDismissRequest = { vm.openEqSheet(false) },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            containerColor = VoxColors.BgElevated,
        ) {
            EqualizerSheet(
                state = state,
                onDismiss = { vm.openEqSheet(false) },
                onEnable = { on ->
                    if (on) {
                        if (state.eqPreset == EqualizerControl.PRESET_OFF) {
                            vm.setEqPreset(EqualizerControl.PRESET_CUSTOM)
                        }
                    } else {
                        vm.setEqPreset(EqualizerControl.PRESET_OFF)
                    }
                },
                onPreset = vm::setEqPreset,
                onBand = vm::setEqBandDb,
                onPreamp = vm::setEqPreampDb,
                onSnap = vm::setEqSnapBands,
                onReset = vm::resetEqBands,
            )
        }
    }
}

@Composable
private fun AddToListSheet(
    trackTitle: String,
    playlists: List<LocalPlaylistStore.Playlist>,
    onPick: (String) -> Unit,
    onCreateNew: () -> Unit,
    onDismiss: () -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(start = 20.dp, end = 20.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            "Add to list",
            style = MaterialTheme.typography.titleLarge,
            color = VoxColors.Accent,
        )
        Text(
            trackTitle,
            style = MaterialTheme.typography.bodyMedium,
            color = VoxColors.TextSecondary,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        AccentButton("New list + add", onCreateNew, Modifier.fillMaxWidth())
        if (playlists.isEmpty()) {
            Text(
                "No folders yet — New list creates one and adds this track.",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
        } else {
            Text(
                "Existing folders",
                style = MaterialTheme.typography.titleMedium,
                color = VoxColors.Accent,
            )
            playlists.forEach { pl ->
                Text(
                    "${pl.name} · ${pl.tracks.size} tracks",
                    Modifier
                        .fillMaxWidth()
                        .clip(VoxShapes.card)
                        .background(VoxColors.BgPanel)
                        .clickable { onPick(pl.id) }
                        .padding(horizontal = 12.dp, vertical = 12.dp),
                    style = MaterialTheme.typography.bodyLarge,
                    color = VoxColors.Text,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        QuietButton("Cancel", onDismiss, Modifier.fillMaxWidth())
    }
}

private fun PlayerUiState.primaryDest(): PrimaryDest = when {
    tab == AppTab.Connect -> PrimaryDest.More
    localFilter == "video" -> PrimaryDest.Video
    localFilter == "audio" -> PrimaryDest.Audio
    localFilter == "lists" -> PrimaryDest.Lists
    localFilter == "browse" -> PrimaryDest.Browse
    localFilter == "all" || localFilter == "recent" || localFilter == "top" ||
        localFilter == "week" || localFilter == "month" -> PrimaryDest.Home
    else -> PrimaryDest.Home
}

@Composable
private fun CompactPanelChrome(
    state: PlayerUiState,
    onSelectDest: (PrimaryDest) -> Unit,
    onConnect: () -> Unit,
) {
    val selected = state.primaryDest()
    Row(
        Modifier
            .fillMaxWidth()
            .background(VoxColors.BgPanel)
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text("VX", color = VoxColors.Accent, fontWeight = FontWeight.Bold, fontSize = 13.sp)
        listOf(
            PrimaryDest.Home to "Home",
            PrimaryDest.Video to "Video",
            PrimaryDest.Audio to "Audio",
            PrimaryDest.Browse to "Browse",
            PrimaryDest.Lists to "Lists",
            PrimaryDest.More to "More",
        ).forEach { (dest, label) ->
            QuietButton(
                if (selected == dest) "· $label" else label,
                { onSelectDest(dest) },
            )
        }
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
        IconButton(onClick = onConnect) {
            Icon(
                Icons.Default.Devices,
                contentDescription = "Connect desktop",
                tint = if (state.activeOutput.startsWith("Desktop")) VoxColors.Success else VoxColors.Accent,
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
    labeled: Boolean,
    onSelectDest: (PrimaryDest) -> Unit,
    onOpen: () -> Unit,
    onConnect: () -> Unit,
) {
    val selected = state.primaryDest()
    val dests = listOf(
        Triple(PrimaryDest.Home, "Home", Icons.Default.Home),
        Triple(PrimaryDest.Video, "Video", Icons.Default.Movie),
        Triple(PrimaryDest.Audio, "Audio", Icons.Default.AudioFile),
        Triple(PrimaryDest.Browse, "Browse", Icons.Default.FolderOpen),
        Triple(PrimaryDest.Lists, "Lists", Icons.Default.QueueMusic),
        Triple(PrimaryDest.More, "More", Icons.Default.MoreHoriz),
    )
    Column(
        Modifier
            .width(if (labeled) 88.dp else 64.dp)
            .fillMaxHeight()
            .background(VoxColors.Rail)
            .padding(vertical = 10.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(if (labeled) 4.dp else 8.dp),
    ) {
        Box(
            Modifier
                .size(if (labeled) 36.dp else 40.dp)
                .clip(RoundedCornerShapeCompat)
                .background(VoxColors.AccentSoft),
            contentAlignment = Alignment.Center,
        ) {
            Text("VX", color = VoxColors.Accent, fontWeight = FontWeight.Bold, fontSize = 14.sp)
        }
        Spacer(Modifier.height(4.dp))
        dests.forEach { (dest, label, icon) ->
            if (labeled) {
                RailLabeledBtn(icon, label, selected == dest) { onSelectDest(dest) }
            } else {
                RailBtn(icon, label, selected == dest) { onSelectDest(dest) }
            }
        }
        Spacer(Modifier.weight(1f))
        if (labeled) {
            RailLabeledBtn(Icons.Default.PlayArrow, "Open", false, onOpen)
            RailLabeledBtn(
                Icons.Default.Devices,
                "Link",
                state.activeOutput.startsWith("Desktop"),
                onConnect,
            )
        } else {
            RailBtn(Icons.Default.PlayArrow, "Open file", false, onOpen)
            RailBtn(
                Icons.Default.Devices,
                "Connect",
                state.activeOutput.startsWith("Desktop"),
                onConnect,
            )
        }
    }
}

@Composable
private fun PrimaryDestBar(
    selected: PrimaryDest,
    onSelect: (PrimaryDest) -> Unit,
) {
    val items = listOf(
        Triple(PrimaryDest.Home, "Home", Icons.Default.Home),
        Triple(PrimaryDest.Video, "Video", Icons.Default.Movie),
        Triple(PrimaryDest.Audio, "Audio", Icons.Default.AudioFile),
        Triple(PrimaryDest.Browse, "Browse", Icons.Default.FolderOpen),
        Triple(PrimaryDest.Lists, "Lists", Icons.Default.QueueMusic),
        Triple(PrimaryDest.More, "More", Icons.Default.MoreHoriz),
    )
    NavigationBar(
        containerColor = VoxColors.BgPanel,
        contentColor = VoxColors.Text,
        tonalElevation = 0.dp,
    ) {
        items.forEach { (dest, label, icon) ->
            val active = selected == dest
            NavigationBarItem(
                selected = active,
                onClick = { onSelect(dest) },
                icon = {
                    Icon(
                        icon,
                        contentDescription = label,
                        modifier = Modifier.size(22.dp),
                    )
                },
                label = {
                    Text(
                        label,
                        style = MaterialTheme.typography.labelSmall,
                        maxLines = 1,
                    )
                },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = VoxColors.Accent,
                    selectedTextColor = VoxColors.Accent,
                    indicatorColor = VoxColors.AccentSoft,
                    unselectedIconColor = VoxColors.TextSecondary,
                    unselectedTextColor = VoxColors.TextMuted,
                ),
            )
        }
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
            .clickable(onClick = onClick)
            .semantics { contentDescription = tip },
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

/** Quest / lean rail: icon + short label for controller pointing (streaming + FOSS panel pattern). */
@Composable
private fun RailLabeledBtn(icon: ImageVector, label: String, active: Boolean, onClick: () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 6.dp)
            .clip(RoundedCornerShape(10.dp))
            .background(if (active) VoxColors.AccentSoft else androidx.compose.ui.graphics.Color.Transparent)
            .clickable(onClick = onClick)
            .semantics { contentDescription = label }
            .padding(vertical = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Icon(
            icon,
            contentDescription = label,
            tint = if (active) VoxColors.Accent else VoxColors.TextSecondary,
            modifier = Modifier.size(22.dp),
        )
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            color = if (active) VoxColors.Accent else VoxColors.TextMuted,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            fontSize = 10.sp,
        )
    }
}

@Composable
private fun ShellHeader(
    state: PlayerUiState,
    wide: Boolean,
    onConnect: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .background(VoxColors.BgApp)
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                "VoxPlayer",
                style = MaterialTheme.typography.titleLarge,
                color = VoxColors.Accent,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                if (wide) "Library · remote" else "On-device library",
                style = MaterialTheme.typography.labelMedium,
                color = VoxColors.TextMuted,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Text(
            state.activeOutput,
            color = if (state.activeOutput.startsWith("Desktop")) VoxColors.Success else VoxColors.TextMuted,
            style = MaterialTheme.typography.labelMedium,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.widthIn(max = 96.dp),
        )
        IconButton(onClick = onConnect) {
            Icon(
                Icons.Default.Devices,
                contentDescription = "Connect desktop",
                tint = if (state.activeOutput.startsWith("Desktop")) VoxColors.Success else VoxColors.Accent,
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LocalLibraryPane(
    state: PlayerUiState,
    player: Player?,
    wide: Boolean,
    railChrome: Boolean,
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
    onAddListsTrackToList: (LocalPlaylistStore.Track) -> Unit,
    onAddNowPlayingTo: (String) -> Unit,
    onImportM3u: () -> Unit,
    onExportPlaylistM3u: (String) -> Unit,
    onFilter: (String) -> Unit,
    onPinFilter: (String) -> Unit,
    onAudioFacet: (String) -> Unit,
    onPlayArtist: (String) -> Unit,
    onPlayAlbum: (String, String) -> Unit,
    onBrowseShortcut: (String, String) -> Unit,
    onBrowseFavorite: (BrowseStore.FavoriteFolder) -> Unit,
    onBrowseInternal: () -> Unit,
    onBrowseBack: () -> Unit,
    onAddBrowseFolder: () -> Unit,
    onRemoveBrowseFavorite: (String) -> Unit,
    onSearch: (String) -> Unit,
    onHomeAzLetter: (Char?) -> Unit,
    onRefreshLibrary: () -> Unit,
    onAddToList: (LocalMediaItem) -> Unit,
    onAddHistoryToList: (PlayHistoryStore.Entry) -> Unit,
    onSeekLocal: (Long) -> Unit,
    onSetVolume: (Int) -> Unit,
    onEnterPip: () -> Unit,
    onOpenPlayerSettings: () -> Unit,
    onOpenCaptions: () -> Unit,
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
        // Video / Audio / Home: library-first — playback lives in mini-player + Now Playing stage
        // (no inline hero surface or redundant Open row; Open file stays on Browse / rail).

        if (state.localFilter == "browse") {
            BrowsePane(
                state = state,
                railChrome = railChrome,
                onShortcut = onBrowseShortcut,
                onFavorite = onBrowseFavorite,
                onInternal = onBrowseInternal,
                onBack = onBrowseBack,
                onAddFolder = onAddBrowseFolder,
                onRemoveFavorite = onRemoveBrowseFavorite,
                onPlay = onPlay,
                onAddToList = onAddToList,
                onOpenFile = onOpenFile,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(top = 8.dp),
            )
            return
        }

        val homeFacet = state.localFilter == "all" || state.localFilter == "recent" ||
            state.localFilter == "top" || state.localFilter == "week" ||
            state.localFilter == "month"
        if (homeFacet) {
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp)
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                listOf(
                    "all" to "Library",
                    "recent" to "Recent",
                    "top" to "Top",
                    "week" to "Week",
                    "month" to "Month",
                ).forEach { (key, label) ->
                    HomeFilterChip(
                        label = label,
                        selected = state.localFilter == key,
                        preferred = state.localFilterPreferred == key,
                        onSelect = { onFilter(key) },
                        onPin = { onPinFilter(key) },
                    )
                }
            }
        }

        if (state.localFilter == "audio") {
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp)
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                listOf(
                    "artists" to "Artists",
                    "albums" to "Albums",
                    "tracks" to "Tracks",
                ).forEach { (k, label) ->
                    FilterChip(
                        selected = state.audioFacet == k,
                        onClick = { onAudioFacet(k) },
                        label = { Text(label) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = VoxColors.AccentSoft,
                            selectedLabelColor = VoxColors.Accent,
                            containerColor = VoxColors.BgElevated,
                            labelColor = VoxColors.Text,
                        ),
                        border = FilterChipDefaults.filterChipBorder(
                            enabled = true,
                            selected = state.audioFacet == k,
                            borderColor = VoxColors.BorderSoft,
                            selectedBorderColor = VoxColors.Accent,
                        ),
                    )
                }
            }
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
        val audioArtists = remember(filtered, state.localFilter, state.audioFacet) {
            if (state.localFilter != "audio" || state.audioFacet != "artists") emptyList()
            else groupAudioArtists(filtered)
        }
        val audioAlbums = remember(filtered, state.localFilter, state.audioFacet) {
            if (state.localFilter != "audio" || state.audioFacet != "albums") emptyList()
            else groupAudioAlbums(filtered)
        }
        val audioGrouped = state.localFilter == "audio" && state.audioFacet != "tracks"

        val homeTitle = when {
            state.localFilter == "recent" -> "Recently played"
            state.localFilter == "top" -> "Most played"
            state.localFilter == "week" -> "This week"
            state.localFilter == "month" -> "This month"
            listsFacet && state.listsBrowseId != null -> "List"
            listsFacet -> "Lists"
            state.localFilter == "audio" && state.audioFacet == "artists" -> "Artists"
            state.localFilter == "audio" && state.audioFacet == "albums" -> "Albums"
            state.localFilter == "audio" -> "Tracks"
            state.localFilter == "video" -> "Video"
            else -> "Home"
        }
        val homeCount = when {
            historyFacet -> historyRows.size
            listsFacet && state.listsBrowseId != null -> 0
            listsFacet -> state.localPlaylists.size
            state.localFilter == "audio" && state.audioFacet == "artists" -> audioArtists.size
            state.localFilter == "audio" && state.audioFacet == "albums" -> audioAlbums.size
            else -> filtered.size
        }
        val homeCountLabel = when {
            listsFacet && state.listsBrowseId != null -> null
            listsFacet -> "$homeCount folders"
            state.localFilter == "audio" && state.audioFacet == "artists" -> "$homeCount artists"
            state.localFilter == "audio" && state.audioFacet == "albums" -> "$homeCount albums"
            historyFacet -> "$homeCount"
            q.isNotEmpty() && state.localItems.isNotEmpty() ->
                "$homeCount / ${state.localItems.size}"
            else -> "$homeCount"
        }
        Row(
            Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                homeTitle,
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.weight(1f),
            )
            if (homeCountLabel != null) {
                Text(
                    homeCountLabel,
                    Modifier
                        .clip(VoxShapes.pill)
                        .background(VoxColors.AccentSoft)
                        .border(1.dp, VoxColors.Accent, VoxShapes.pill)
                        .padding(horizontal = 10.dp, vertical = 4.dp)
                        .semantics {
                            contentDescription = when {
                                listsFacet -> "$homeCount playlist folders"
                                historyFacet -> "$homeCount history items"
                                else -> "$homeCount library items shown"
                            }
                        },
                    style = MaterialTheme.typography.labelMedium,
                    color = VoxColors.Accent,
                    maxLines = 1,
                )
            }
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
                onAddListsTrackToList = onAddListsTrackToList,
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
        PullToRefreshBox(
            isRefreshing = state.libraryRefreshing,
            onRefresh = onRefreshLibrary,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
        ) {
            if (historyFacet) {
                if (historyRows.isEmpty()) {
                    LibraryEmptyTips(
                        filter = state.localFilter,
                        searchActive = q.isNotEmpty(),
                        onOpenFile = onOpenFile,
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
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
                            HistoryCard(
                                entry = entry,
                                facet = state.localFilter,
                                onClick = { onPlayHistory(entry) },
                                onLongClick = { onAddHistoryToList(entry) },
                            )
                        }
                    }
                }
            } else if (audioGrouped && state.audioFacet == "artists") {
                if (audioArtists.isEmpty()) {
                    LibraryEmptyTips(
                        filter = state.localFilter,
                        searchActive = q.isNotEmpty(),
                        libraryTotal = state.localItems.size,
                        onOpenFile = onOpenFile,
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(vertical = 24.dp),
                    )
                } else {
                    AudioArtistGrid(
                        artists = audioArtists,
                        cols = cols,
                        onPlayArtist = onPlayArtist,
                        modifier = Modifier.fillMaxSize(),
                    )
                }
            } else if (audioGrouped && state.audioFacet == "albums") {
                if (audioAlbums.isEmpty()) {
                    LibraryEmptyTips(
                        filter = state.localFilter,
                        searchActive = q.isNotEmpty(),
                        libraryTotal = state.localItems.size,
                        onOpenFile = onOpenFile,
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(vertical = 24.dp),
                    )
                } else {
                    AudioAlbumGrid(
                        albums = audioAlbums,
                        cols = cols,
                        onPlayAlbum = onPlayAlbum,
                        modifier = Modifier.fillMaxSize(),
                    )
                }
            } else if (filtered.isEmpty()) {
                LibraryEmptyTips(
                    filter = state.localFilter,
                    searchActive = q.isNotEmpty(),
                    libraryTotal = state.localItems.size,
                    onOpenFile = onOpenFile,
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(vertical = 24.dp),
                )
            } else {
                AzLibraryGrid(
                    items = filtered,
                    cols = cols,
                    initialLetter = state.homeAzLetter,
                    onLetterChanged = onHomeAzLetter,
                    onPlay = onPlay,
                    onAddToList = onAddToList,
                    modifier = Modifier.fillMaxSize(),
                )
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun BrowsePane(
    state: PlayerUiState,
    railChrome: Boolean,
    onShortcut: (String, String) -> Unit,
    onFavorite: (BrowseStore.FavoriteFolder) -> Unit,
    onInternal: () -> Unit,
    onBack: () -> Unit,
    onAddFolder: () -> Unit,
    onRemoveFavorite: (String) -> Unit,
    onPlay: (LocalMediaItem) -> Unit,
    onAddToList: (LocalMediaItem) -> Unit,
    onOpenFile: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val inFolder = state.browseFolderTitle.isNotBlank()
    Column(modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                if (inFolder) state.browseFolderTitle else "Browse",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.weight(1f),
            )
            if (inFolder) {
                Text(
                    "${state.browseFolderItems.size}",
                    Modifier
                        .clip(VoxShapes.pill)
                        .background(VoxColors.AccentSoft)
                        .border(1.dp, VoxColors.Accent, VoxShapes.pill)
                        .padding(horizontal = 10.dp, vertical = 4.dp),
                    style = MaterialTheme.typography.labelMedium,
                    color = VoxColors.Accent,
                )
                QuietButton("Back", onBack)
            } else {
                QuietButton("Add folder…", onAddFolder)
                // Rail already exposes Open — avoid duplicate chrome on Quest/tablet.
                if (!railChrome) {
                    QuietButton("Open file", onOpenFile)
                }
            }
        }
        if (!inFolder) {
            Text(
                "On-device folders · SAF picker · no cloud",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            Column(
                Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text("Favorites", style = MaterialTheme.typography.titleSmall, color = VoxColors.Accent)
                val shortcutCards = listOf(
                    Triple("Download", "Download", Icons.Default.Download),
                    Triple("Movies", "Movies", Icons.Default.Movie),
                    Triple("Music", "Music", Icons.Default.LibraryMusic),
                    Triple("Podcasts", "Podcasts", Icons.Default.Podcasts),
                )
                shortcutCards.chunked(2).forEach { row ->
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        row.forEach { (label, hint, icon) ->
                            BrowseFolderCard(
                                title = label,
                                subtitle = "MediaStore · $hint/",
                                icon = icon,
                                onClick = { onShortcut(label, hint) },
                                modifier = Modifier.weight(1f),
                            )
                        }
                        if (row.size == 1) Spacer(Modifier.weight(1f))
                    }
                }
                state.browseFavorites.chunked(2).forEach { row ->
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        row.forEach { fav ->
                            BrowseFolderCard(
                                title = fav.label,
                                subtitle = "SAF favorite · long-press remove",
                                icon = Icons.Default.Folder,
                                onClick = { onFavorite(fav) },
                                onLongClick = { onRemoveFavorite(fav.id) },
                                modifier = Modifier.weight(1f),
                            )
                        }
                        if (row.size == 1) Spacer(Modifier.weight(1f))
                    }
                }
                BrowseFolderCard(
                    title = "Add folder…",
                    subtitle = "Persist SAF grant",
                    icon = Icons.Default.Add,
                    onClick = onAddFolder,
                    modifier = Modifier.fillMaxWidth(),
                )
                Text(
                    "Storages",
                    style = MaterialTheme.typography.titleSmall,
                    color = VoxColors.Accent,
                    modifier = Modifier.padding(top = 8.dp),
                )
                BrowseFolderCard(
                    title = "Internal storage",
                    subtitle = "${state.localItems.size} MediaStore items",
                    icon = Icons.Default.Storage,
                    onClick = onInternal,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        } else if (state.browseFolderItems.isEmpty()) {
            LibraryEmptyTips(
                filter = "browse",
                searchActive = false,
                libraryTotal = state.localItems.size,
                onOpenFile = onOpenFile,
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(vertical = 12.dp),
            )
        } else {
            AzLibraryGrid(
                items = state.browseFolderItems,
                cols = 2,
                initialLetter = null,
                onLetterChanged = {},
                onPlay = onPlay,
                onAddToList = onAddToList,
                modifier = Modifier.weight(1f).fillMaxWidth(),
            )
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun BrowseFolderCard(
    title: String,
    subtitle: String,
    icon: ImageVector,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    onLongClick: (() -> Unit)? = null,
) {
    val haptics = LocalHapticFeedback.current
    Column(
        modifier
            .clip(VoxShapes.card)
            .background(VoxColors.BgElevated)
            .border(1.dp, VoxColors.BorderSoft, VoxShapes.card)
            .combinedClickable(
                onClick = onClick,
                onLongClick = onLongClick?.let {
                    {
                        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                        it()
                    }
                },
            )
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Box(
            Modifier
                .size(40.dp)
                .clip(VoxShapes.art)
                .background(VoxColors.AccentSoft),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, contentDescription = null, tint = VoxColors.Accent, modifier = Modifier.size(22.dp))
        }
        Text(
            title,
            style = MaterialTheme.typography.titleSmall,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            color = VoxColors.Text,
        )
        Text(
            subtitle,
            style = MaterialTheme.typography.bodySmall,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            color = VoxColors.TextMuted,
        )
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
        filter == "browse" -> "Nothing in this folder" to "MediaStore may not index this path yet, or the SAF folder has no audio/video. Use Add folder… or Open file (GrapheneOS Storage Scopes friendly)."
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
            "Tips: Long-press a card to add to a list · All / Audio / Video browse MediaStore · Recent / Top / Week / Month are local history · Lists for folders & M3U",
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

private const val UI_UNKNOWN_ARTIST = "Unknown artist"
private const val UI_UNKNOWN_ALBUM = "Unknown album"

private data class AudioArtistGroup(
    val name: String,
    val albumCount: Int,
    val trackCount: Int,
    val sample: LocalMediaItem,
)

private data class AudioAlbumGroup(
    val album: String,
    val artist: String,
    val trackCount: Int,
    val sample: LocalMediaItem,
)

private fun groupAudioArtists(items: List<LocalMediaItem>): List<AudioArtistGroup> =
    items.groupBy { it.artist.trim().ifBlank { UI_UNKNOWN_ARTIST } }
        .map { (name, tracks) ->
            AudioArtistGroup(
                name = name,
                albumCount = tracks.map { it.album.trim().ifBlank { UI_UNKNOWN_ALBUM } }.distinct().size,
                trackCount = tracks.size,
                sample = tracks.first(),
            )
        }
        .sortedWith(compareBy(String.CASE_INSENSITIVE_ORDER) { it.name })

private fun groupAudioAlbums(items: List<LocalMediaItem>): List<AudioAlbumGroup> =
    items.groupBy {
        (it.album.trim().ifBlank { UI_UNKNOWN_ALBUM }) to
            (it.artist.trim().ifBlank { UI_UNKNOWN_ARTIST })
    }
        .map { (key, tracks) ->
            AudioAlbumGroup(
                album = key.first,
                artist = key.second,
                trackCount = tracks.size,
                sample = tracks.first(),
            )
        }
        .sortedWith(
            compareBy(
                { it.album.lowercase() },
                { it.artist.lowercase() },
            ),
        )

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun AudioArtistGrid(
    artists: List<AudioArtistGroup>,
    cols: Int,
    onPlayArtist: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val grouped = remember(artists) {
        artists.groupBy { libraryIndexLetter(it.name) }
            .toSortedMap(compareBy { if (it == '#') '@' else it })
    }
    LazyVerticalGrid(
        columns = GridCells.Fixed(cols),
        contentPadding = PaddingValues(bottom = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        modifier = modifier,
    ) {
        grouped.forEach { (letter, rows) ->
            item(span = { GridItemSpan(cols) }, key = "a-letter-$letter") {
                Text(
                    letter.toString(),
                    style = MaterialTheme.typography.titleLarge,
                    color = VoxColors.Accent,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            items(rows, key = { "artist-${it.name}" }) { row ->
                AudioGroupCard(
                    title = row.name,
                    subtitle = when {
                        row.albumCount == 1 -> "1 album · ${row.trackCount} tracks"
                        else -> "${row.albumCount} albums · ${row.trackCount} tracks"
                    },
                    sample = row.sample,
                    onPlay = { onPlayArtist(row.name) },
                )
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun AudioAlbumGrid(
    albums: List<AudioAlbumGroup>,
    cols: Int,
    onPlayAlbum: (String, String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val grouped = remember(albums) {
        albums.groupBy { libraryIndexLetter(it.album) }
            .toSortedMap(compareBy { if (it == '#') '@' else it })
    }
    LazyVerticalGrid(
        columns = GridCells.Fixed(cols),
        contentPadding = PaddingValues(bottom = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        modifier = modifier,
    ) {
        grouped.forEach { (letter, rows) ->
            item(span = { GridItemSpan(cols) }, key = "alb-letter-$letter") {
                Text(
                    letter.toString(),
                    style = MaterialTheme.typography.titleLarge,
                    color = VoxColors.Accent,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            items(rows, key = { "album-${it.artist}-${it.album}" }) { row ->
                AudioGroupCard(
                    title = row.album,
                    subtitle = "${row.artist} · ${row.trackCount} tracks",
                    sample = row.sample,
                    onPlay = { onPlayAlbum(row.album, row.artist) },
                )
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun AudioGroupCard(
    title: String,
    subtitle: String,
    sample: LocalMediaItem,
    onPlay: () -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(VoxShapes.card)
            .background(VoxColors.BgElevated)
            .combinedClickable(onClick = onPlay)
            .semantics {
                contentDescription = "$title. $subtitle. Double-tap to play."
            }
            .padding(8.dp),
    ) {
        Box(
            Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .clip(VoxShapes.art)
                .background(VoxColors.BgPanel),
        ) {
            ArtworkThumb(
                contentUri = sample.artworkContentUri(),
                isVideo = sample.isVideo,
                modifier = Modifier.fillMaxSize(),
            )
            Box(
                Modifier
                    .align(Alignment.BottomEnd)
                    .padding(8.dp)
                    .size(36.dp)
                    .clip(CircleShape)
                    .background(VoxColors.Accent)
                    .clickable(onClick = onPlay),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Default.PlayArrow,
                    contentDescription = "Play $title",
                    tint = VoxColors.BgApp,
                    modifier = Modifier.size(22.dp),
                )
            }
        }
        Spacer(Modifier.height(8.dp))
        Text(
            title,
            style = MaterialTheme.typography.titleSmall,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            color = VoxColors.Text,
        )
        Text(
            subtitle,
            style = MaterialTheme.typography.bodySmall,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            color = VoxColors.TextMuted,
        )
    }
}

@Composable
private fun AzLibraryGrid(
    items: List<LocalMediaItem>,
    cols: Int,
    initialLetter: Char?,
    onLetterChanged: (Char?) -> Unit,
    onPlay: (LocalMediaItem) -> Unit,
    onAddToList: (LocalMediaItem) -> Unit,
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
    val letterByFlatIndex = remember(letterStartIndex) {
        letterStartIndex.entries
            .sortedBy { it.value }
            .map { it.key to it.value }
    }
    val gridState = rememberLazyGridState()
    val scope = rememberCoroutineScope()
    var restored by remember(items) { mutableStateOf(false) }

    LaunchedEffect(letters, initialLetter, letterStartIndex) {
        if (restored || letters.isEmpty()) return@LaunchedEffect
        val letter = initialLetter?.takeIf { it in letters }
        if (letter != null) {
            val target = letterStartIndex[letter] ?: 0
            gridState.scrollToItem(target)
        }
        restored = true
    }

    LaunchedEffect(gridState, letterByFlatIndex) {
        snapshotFlow { gridState.firstVisibleItemIndex }
            .map { index ->
                letterByFlatIndex.lastOrNull { (_, start) -> start <= index }?.first
            }
            .distinctUntilChanged()
            .collect { letter ->
                onLetterChanged(letter)
            }
    }

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
                    MediaCard(
                        item = item,
                        onClick = { onPlay(item) },
                        onLongClick = { onAddToList(item) },
                    )
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
                                onLetterChanged(letter)
                                scope.launch {
                                    gridState.animateScrollToItem(target)
                                }
                            }
                            .padding(horizontal = 4.dp, vertical = 1.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = if (letter == initialLetter) VoxColors.Accent else VoxColors.TextMuted,
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
    onAddListsTrackToList: (LocalPlaylistStore.Track) -> Unit,
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
                LocalPlaylistStore.SMART_FAVORITES to "Favorites",
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
        browse == LocalPlaylistStore.SMART_FAVORITES -> state.bookmarks.map { bm ->
            LocalPlaylistStore.Track(
                bm.uri,
                bm.title,
                "at ${fmtBookmarkPos(bm.positionMs)}",
                "",
                bm.isVideo,
            )
        }
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
            ListsTrackRow(
                track = t,
                canRemove = isUser,
                onPlay = { onPlayListsTrack(t.uri) },
                onAddToList = { onAddListsTrackToList(t) },
                onRemove = { onRemovePlaylistTrack(browse, t.uri) },
            )
        }
        Spacer(Modifier.height(24.dp))
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun ListsTrackRow(
    track: LocalPlaylistStore.Track,
    canRemove: Boolean,
    onPlay: () -> Unit,
    onAddToList: () -> Unit,
    onRemove: () -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    Row(
        Modifier
            .fillMaxWidth()
            .clip(VoxShapes.card)
            .background(VoxColors.BgElevated)
            .combinedClickable(
                onClick = onPlay,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onAddToList()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(track.title)
                    if (track.artist.isNotBlank()) {
                        append(" by ")
                        append(track.artist)
                    }
                    append(". Double-tap to play. Long-press to add to another list.")
                }
            }
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(track.title, style = MaterialTheme.typography.titleSmall, maxLines = 1)
            Text(
                track.artist.ifBlank { if (track.isVideo) "Video" else "Audio" },
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextSecondary,
                maxLines = 1,
            )
        }
        if (canRemove) {
            IconButton(onClick = onRemove, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Default.Close, "Remove", tint = VoxColors.TextMuted)
            }
        }
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

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun HistoryCard(
    entry: PlayHistoryStore.Entry,
    facet: String,
    onClick: () -> Unit,
    onLongClick: () -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    Column(
        Modifier
            .clip(VoxShapes.card)
            .background(VoxColors.BgElevated)
            .combinedClickable(
                onClick = onClick,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onLongClick()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(entry.title)
                    if (entry.artist.isNotBlank()) {
                        append(" by ")
                        append(entry.artist)
                    }
                    append(". Double-tap to play. Long-press to add to a list.")
                }
            }
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

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun MediaCard(
    item: LocalMediaItem,
    onClick: () -> Unit,
    onLongClick: () -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    Column(
        Modifier
            .clip(VoxShapes.card)
            .background(VoxColors.BgElevated)
            .combinedClickable(
                onClick = onClick,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onLongClick()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(item.title)
                    if (item.artist.isNotBlank()) {
                        append(" by ")
                        append(item.artist)
                    }
                    append(". Double-tap to play. Long-press to add to a list.")
                }
            }
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

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun NowPlayingPane(
    state: PlayerUiState,
    player: Player?,
    onPlayPause: () -> Unit,
    onShuffle: () -> Unit,
    onPinShuffle: () -> Unit,
    onRepeat: () -> Unit,
    onSetRepeat: (Int) -> Unit,
    onPinRepeat: (Int) -> Unit,
    onVolDown: () -> Unit,
    onVolUp: () -> Unit,
    onMute: () -> Unit,
    onRefreshDevices: () -> Unit,
    onSelectDevice: (Int) -> Unit,
    onPinDevice: (Int) -> Unit,
    onEqPreset: (String) -> Unit,
    onPinEqPreset: (String) -> Unit,
    onOpenEqSheet: () -> Unit,
    onSleepMinutes: (Int) -> Unit,
    onPinSleepMinutes: (Int) -> Unit,
    onStartPreferredSleep: () -> Unit,
    onClearSleep: () -> Unit,
    onToggleCrossfade: () -> Unit,
    onToggleSkipSilence: () -> Unit,
    onFadeMs: (Long) -> Unit,
    onPinFadeMs: (Long) -> Unit,
    onPlaybackSpeed: (Float) -> Unit,
    onPinPlaybackSpeed: (Float) -> Unit,
    onToggleDlna: () -> Unit,
    onScanDlna: () -> Unit,
    onSelectDlna: (String) -> Unit,
    onSetDefaultDlna: (String) -> Unit,
    onCastDlna: () -> Unit,
    onDlnaPlay: () -> Unit,
    onDlnaPause: () -> Unit,
    onDlnaStop: () -> Unit,
    onShareNowPlaying: () -> Unit,
    onExportQueueM3u: () -> Unit,
    onBookmarkNow: () -> Unit,
    onPlayBookmark: (BookmarkStore.Bookmark) -> Unit,
    onRemoveBookmark: (String) -> Unit,
    onAddBookmarkToList: (BookmarkStore.Bookmark) -> Unit,
    onClearBookmarks: () -> Unit,
    onClearPreferredPins: () -> Unit,
    onClearTrackResume: () -> Unit,
    onSeekLocal: (Long) -> Unit,
    onSetVolume: (Int) -> Unit,
    onEnterPip: () -> Unit,
    onPlayQueueIndex: (Int) -> Unit,
    onMoveQueue: (Int, Int) -> Unit,
    onRemoveQueue: (Int) -> Unit,
    onAddQueueToList: (QueueRow) -> Unit,
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
        val sideVideo = player != null && !desktop && state.localIsVideo && title != "(nothing loaded)"
        Box(
            Modifier
                .fillMaxWidth()
                .then(
                    if (sideVideo) Modifier.aspectRatio(16f / 9f)
                    else Modifier.aspectRatio(1f),
                )
                .clip(VoxShapes.panel)
                .background(VoxColors.BgElevated),
            contentAlignment = Alignment.Center,
        ) {
            if (sideVideo) {
                VideoGestureSurface(
                    positionMs = state.localPositionMs,
                    durationMs = state.localDurationMs,
                    volumePercent = state.localVolume,
                    onSeek = onSeekLocal,
                    onVolumePercent = onSetVolume,
                    modifier = Modifier.fillMaxSize(),
                ) {
                    AndroidView(
                        factory = { ctx -> PlayerSurfaces.attachPlayerHost(ctx, player) },
                        update = { host -> host.bind(player) },
                        modifier = Modifier.fillMaxSize(),
                    )
                }
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
        if (!desktop && state.pipAvailable && state.localIsVideo && title != "(nothing loaded)") {
            QuietButton("Picture-in-picture", onEnterPip, Modifier.fillMaxWidth())
        }
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
                ShufflePinChip(
                    shuffleOn = state.localShuffle,
                    preferred = state.localShufflePreferred,
                    onToggle = onShuffle,
                    onPin = onPinShuffle,
                    modifier = Modifier.weight(1f),
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
                "Long-press Shuffle to pin preferred on. Tap Off/All/One · long-press pin preferred repeat.",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                listOf(
                    Media3Player.REPEAT_MODE_OFF to "Off",
                    Media3Player.REPEAT_MODE_ALL to "All",
                    Media3Player.REPEAT_MODE_ONE to "One",
                ).forEach { (mode, label) ->
                    RepeatModeChip(
                        label = label,
                        selected = state.localRepeatMode == mode,
                        preferred = state.localRepeatPreferred == mode,
                        onSelect = { onSetRepeat(mode) },
                        onPin = { onPinRepeat(mode) },
                        modifier = Modifier.weight(1f),
                    )
                }
            }
            Text(
                "Sound output",
                style = MaterialTheme.typography.titleMedium,
                color = VoxColors.Accent,
                modifier = markSection("out"),
            )
            Text(
                "Tap to route. Long-press to pin preferred (reconnect restores by name).",
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
            val pinActive = state.audioPinName.isNotEmpty()
            val selectedName = when {
                usingDefault && pinActive ->
                    "Routing: System default (waiting · ${state.audioPinName})"
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
                    val pinned = state.audioPinName.isNotEmpty() &&
                        state.audioPinType == dev.type &&
                        state.audioPinName.equals(dev.name, ignoreCase = true)
                    AudioSinkRow(
                        device = dev,
                        selected = selected,
                        pinned = pinned,
                        onSelect = { onSelectDevice(dev.id) },
                        onPin = { onPinDevice(dev.id) },
                    )
                }
            }
            Row(
                Modifier
                    .fillMaxWidth()
                    .then(markSection("eq")),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text(
                    "Equalizer",
                    style = MaterialTheme.typography.titleMedium,
                    color = VoxColors.Accent,
                    modifier = Modifier.weight(1f),
                )
                QuietButton("10-band", onOpenEqSheet)
            }
            Text(
                "Tap preset to apply · long-press pin preferred. Open 10-band for preamp, bands, and snap.",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            EqualizerControl.PRESETS.chunked(3).forEach { row ->
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    row.forEach { (id, label) ->
                        EqPresetChip(
                            label = label,
                            selected = state.eqPreset == id,
                            preferred = state.eqPreferredId == id,
                            onSelect = { onEqPreset(id) },
                            onPin = { onPinEqPreset(id) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                    repeat(3 - row.size) {
                        Spacer(Modifier.weight(1f))
                    }
                }
            }
            Text(
                buildString {
                    append(EqualizerControl.describe(state.eqPreset))
                    if (state.eqPreset == EqualizerControl.PRESET_CUSTOM) {
                        append(" · Preamp ")
                        append(EqualizerControl.formatDb(state.eqPreampDb))
                    }
                    if (state.eqPreferredId.isNotEmpty()) {
                        append(" · Preferred ")
                        append(EqualizerControl.label(state.eqPreferredId))
                    }
                },
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
                    buildString {
                        append("Tap to apply · long-press pin preferred. Fade ")
                        append(CrossfadeControl.fadeLabel(state.fadeMs))
                        append(" (")
                        append(state.fadeMs)
                        append(" ms)")
                        if (state.fadeMsPreferred > 0L) {
                            append(" · Preferred ")
                            append(CrossfadeControl.fadeLabel(state.fadeMsPreferred))
                        }
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = VoxColors.TextMuted,
                )
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    CrossfadeControl.FADE_OPTIONS.forEach { (ms, label) ->
                        FadePresetChip(
                            label = label,
                            selected = state.fadeMs == ms,
                            preferred = state.fadeMsPreferred == ms,
                            onSelect = { onFadeMs(ms) },
                            onPin = { onPinFadeMs(ms) },
                            modifier = Modifier.weight(1f),
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
                buildString {
                    append("Slider or +/− · long-press label to pin preferred. Now ")
                    append(PlaybackSpeed.label(state.playbackSpeed))
                    if (!state.playbackSpeedPreferred.isNaN()) {
                        append(" · Preferred ")
                        append(PlaybackSpeed.label(state.playbackSpeedPreferred))
                    }
                },
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            // Match PlaybackSpeedSheet / Pixel 1.114.0 — no preset chips (Quest panel + phone).
            Text(
                PlaybackSpeed.label(state.playbackSpeed),
                style = MaterialTheme.typography.headlineSmall,
                color = VoxColors.Text,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier
                    .fillMaxWidth()
                    .combinedClickable(
                        onClick = {},
                        onLongClick = { onPinPlaybackSpeed(state.playbackSpeed) },
                    ),
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            )
            Row(
                Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                IconButton(
                    onClick = {
                        onPlaybackSpeed(
                            (state.playbackSpeed - 0.05f).coerceIn(PlaybackSpeed.MIN, PlaybackSpeed.MAX),
                        )
                    },
                ) {
                    Icon(Icons.Default.Remove, contentDescription = "Slower", tint = VoxColors.Text)
                }
                Slider(
                    value = state.playbackSpeed.coerceIn(PlaybackSpeed.MIN, PlaybackSpeed.MAX),
                    onValueChange = onPlaybackSpeed,
                    valueRange = PlaybackSpeed.MIN..PlaybackSpeed.MAX,
                    modifier = Modifier.weight(1f),
                    colors = SliderDefaults.colors(
                        thumbColor = VoxColors.Text,
                        activeTrackColor = VoxColors.Text,
                        inactiveTrackColor = VoxColors.BorderSoft,
                    ),
                )
                IconButton(
                    onClick = {
                        onPlaybackSpeed(
                            (state.playbackSpeed + 0.05f).coerceIn(PlaybackSpeed.MIN, PlaybackSpeed.MAX),
                        )
                    },
                ) {
                    Icon(Icons.Default.Add, contentDescription = "Faster", tint = VoxColors.Text)
                }
            }
            Text("DLNA cast", style = MaterialTheme.typography.titleMedium, color = VoxColors.Accent)
            Text(
                "LAN MediaRenderer only — no Google Cast / GMS. Long-press a renderer to set / clear default.",
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
                    DlnaRendererRow(
                        renderer = r,
                        selected = state.dlnaSelectedId == r.id,
                        isDefault = state.dlnaDefaultId == r.id,
                        onSelect = { onSelectDlna(r.id) },
                        onSetDefault = { onSetDefaultDlna(r.id) },
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
                buildString {
                    if (state.sleepEndEpochMs > 0L) {
                        append("Ends in ")
                        append(state.sleepRemainingLabel)
                    } else {
                        append("Off · fades then pauses")
                    }
                    append(". Tap to arm · long-press pin preferred")
                    if (state.sleepPreferredMinutes > 0) {
                        append(" (")
                        append(state.sleepPreferredMinutes)
                        append("m)")
                    }
                },
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                SleepTimer.DURATIONS_MIN.take(3).forEach { m ->
                    SleepDurationChip(
                        label = "${m}m",
                        selected = false,
                        preferred = state.sleepPreferredMinutes == m,
                        onSelect = { onSleepMinutes(m) },
                        onPin = { onPinSleepMinutes(m) },
                        modifier = Modifier.weight(1f),
                    )
                }
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                SleepTimer.DURATIONS_MIN.drop(3).forEach { m ->
                    SleepDurationChip(
                        label = "${m}m",
                        selected = false,
                        preferred = state.sleepPreferredMinutes == m,
                        onSelect = { onSleepMinutes(m) },
                        onPin = { onPinSleepMinutes(m) },
                        modifier = Modifier.weight(1f),
                    )
                }
                QuietButton("Off", onClearSleep, Modifier.weight(1f))
            }
            if (state.sleepPreferredMinutes > 0) {
                QuietButton(
                    "Start preferred ${state.sleepPreferredMinutes}m",
                    onStartPreferredSleep,
                    Modifier.fillMaxWidth(),
                )
            }
            Text(
                "Settings",
                style = MaterialTheme.typography.titleMedium,
                color = VoxColors.Accent,
                modifier = markSection("settings"),
            )
            Text(
                "Clear every preferred pin (Home filter, theme, shuffle, repeat, sink, EQ, speed, fade, sleep, DLNA default). Long-press chips still pin individually.",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
            QuietButton(
                "Clear preferred pins",
                onClearPreferredPins,
                Modifier.fillMaxWidth(),
            )
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
                BookmarkRow(
                    bookmark = bm,
                    onPlay = { onPlayBookmark(bm) },
                    onAddToList = { onAddBookmarkToList(bm) },
                    onRemove = { onRemoveBookmark(bm.uri) },
                )
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
                                onAddToList = { onAddQueueToList(row) },
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

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun ThemeModeChip(
    label: String,
    selected: Boolean,
    preferred: Boolean,
    onSelect: () -> Unit,
    onPin: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val haptics = LocalHapticFeedback.current
    val text = buildString {
        if (selected) append("✓ ")
        append(label)
        if (preferred) append(" ★")
    }
    Text(
        text,
        modifier
            .clip(VoxShapes.card)
            .background(
                when {
                    preferred -> VoxColors.AccentSoft
                    selected -> VoxColors.BgPanel
                    else -> VoxColors.BgElevated
                },
            )
            .border(
                1.dp,
                if (preferred) VoxColors.Accent else VoxColors.BorderSoft,
                VoxShapes.card,
            )
            .combinedClickable(
                onClick = onSelect,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onPin()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(label)
                    append(" theme")
                    if (selected) append(", selected")
                    if (preferred) append(", preferred")
                    append(". Double-tap to apply. Long-press to pin or clear preferred.")
                }
            }
            .padding(horizontal = 6.dp, vertical = 8.dp),
        style = MaterialTheme.typography.bodySmall,
        color = if (preferred || selected) VoxColors.Accent else VoxColors.Text,
        maxLines = 1,
        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
    )
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun ShufflePinChip(
    shuffleOn: Boolean,
    preferred: Boolean,
    onToggle: () -> Unit,
    onPin: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val haptics = LocalHapticFeedback.current
    val label = buildString {
        if (shuffleOn) append("✓ ")
        append(if (shuffleOn) "Shuffle on" else "Shuffle")
        if (preferred) append(" ★")
    }
    Text(
        label,
        modifier
            .height(44.dp)
            .clip(VoxShapes.pill)
            .background(
                when {
                    preferred -> VoxColors.AccentSoft
                    shuffleOn -> VoxColors.BgPanel
                    else -> VoxColors.BgElevated
                },
            )
            .border(
                1.dp,
                if (preferred) VoxColors.Accent else VoxColors.BorderSoft,
                VoxShapes.pill,
            )
            .combinedClickable(
                onClick = onToggle,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onPin()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(if (shuffleOn) "Shuffle on" else "Shuffle off")
                    if (preferred) append(", preferred on")
                    append(". Double-tap to toggle. Long-press to pin or clear preferred on.")
                }
            }
            .padding(horizontal = 12.dp, vertical = 10.dp),
        style = MaterialTheme.typography.bodyMedium,
        color = if (preferred || shuffleOn) VoxColors.Accent else VoxColors.Text,
        maxLines = 1,
        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
    )
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun RepeatModeChip(
    label: String,
    selected: Boolean,
    preferred: Boolean,
    onSelect: () -> Unit,
    onPin: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val haptics = LocalHapticFeedback.current
    val text = buildString {
        if (selected) append("✓ ")
        append(label)
        if (preferred) append(" ★")
    }
    Text(
        text,
        modifier
            .clip(VoxShapes.card)
            .background(
                when {
                    preferred -> VoxColors.AccentSoft
                    selected -> VoxColors.BgPanel
                    else -> VoxColors.BgElevated
                },
            )
            .border(
                1.dp,
                if (preferred) VoxColors.Accent else VoxColors.BorderSoft,
                VoxShapes.card,
            )
            .combinedClickable(
                onClick = onSelect,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onPin()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append("Repeat ")
                    append(label)
                    if (selected) append(", selected")
                    if (preferred) append(", preferred")
                    append(". Double-tap to apply. Long-press to pin or clear preferred.")
                }
            }
            .padding(horizontal = 6.dp, vertical = 10.dp),
        style = MaterialTheme.typography.bodySmall,
        color = if (preferred || selected) VoxColors.Accent else VoxColors.Text,
        maxLines = 1,
        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
    )
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun SleepDurationChip(
    label: String,
    selected: Boolean,
    preferred: Boolean,
    onSelect: () -> Unit,
    onPin: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val haptics = LocalHapticFeedback.current
    val text = buildString {
        if (selected) append("✓ ")
        append(label)
        if (preferred) append(" ★")
    }
    Text(
        text,
        modifier
            .clip(VoxShapes.card)
            .background(
                when {
                    preferred -> VoxColors.AccentSoft
                    selected -> VoxColors.BgPanel
                    else -> VoxColors.BgElevated
                },
            )
            .border(
                1.dp,
                if (preferred) VoxColors.Accent else VoxColors.BorderSoft,
                VoxShapes.card,
            )
            .combinedClickable(
                onClick = onSelect,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onPin()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(label)
                    if (preferred) append(", preferred")
                    append(". Double-tap to arm. Long-press to pin or clear preferred.")
                }
            }
            .padding(horizontal = 6.dp, vertical = 10.dp),
        style = MaterialTheme.typography.bodySmall,
        color = if (preferred || selected) VoxColors.Accent else VoxColors.Text,
        maxLines = 1,
        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
    )
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun FadePresetChip(
    label: String,
    selected: Boolean,
    preferred: Boolean,
    onSelect: () -> Unit,
    onPin: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val haptics = LocalHapticFeedback.current
    val text = buildString {
        if (selected) append("✓ ")
        append(label)
        if (preferred) append(" ★")
    }
    Text(
        text,
        modifier
            .clip(VoxShapes.card)
            .background(
                when {
                    preferred -> VoxColors.AccentSoft
                    selected -> VoxColors.BgPanel
                    else -> VoxColors.BgElevated
                },
            )
            .border(
                1.dp,
                if (preferred) VoxColors.Accent else VoxColors.BorderSoft,
                VoxShapes.card,
            )
            .combinedClickable(
                onClick = onSelect,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onPin()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(label)
                    if (selected) append(", selected")
                    if (preferred) append(", preferred")
                    append(". Double-tap to apply. Long-press to pin or clear preferred.")
                }
            }
            .padding(horizontal = 6.dp, vertical = 8.dp),
        style = MaterialTheme.typography.bodySmall,
        color = if (preferred || selected) VoxColors.Accent else VoxColors.Text,
        maxLines = 1,
    )
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun SpeedPresetChip(
    label: String,
    selected: Boolean,
    preferred: Boolean,
    onSelect: () -> Unit,
    onPin: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val haptics = LocalHapticFeedback.current
    val text = buildString {
        if (selected) append("✓ ")
        append(label)
        if (preferred) append(" ★")
    }
    Text(
        text,
        modifier
            .clip(VoxShapes.card)
            .background(
                when {
                    preferred -> VoxColors.AccentSoft
                    selected -> VoxColors.BgPanel
                    else -> VoxColors.BgElevated
                },
            )
            .border(
                1.dp,
                if (preferred) VoxColors.Accent else VoxColors.BorderSoft,
                VoxShapes.card,
            )
            .combinedClickable(
                onClick = onSelect,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onPin()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(label)
                    if (selected) append(", selected")
                    if (preferred) append(", preferred")
                    append(". Double-tap to apply. Long-press to pin or clear preferred.")
                }
            }
            .padding(horizontal = 6.dp, vertical = 8.dp),
        style = MaterialTheme.typography.bodySmall,
        color = if (preferred || selected) VoxColors.Accent else VoxColors.Text,
        maxLines = 1,
    )
}

@Composable
private fun EqualizerSheet(
    state: PlayerUiState,
    onDismiss: () -> Unit,
    onEnable: (Boolean) -> Unit,
    onPreset: (String) -> Unit,
    onBand: (Int, Float) -> Unit,
    onPreamp: (Float) -> Unit,
    onSnap: (Boolean) -> Unit,
    onReset: () -> Unit,
) {
    val enabled = state.eqPreset != EqualizerControl.PRESET_OFF
    Column(
        Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(start = 20.dp, end = 20.dp, bottom = 36.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                "Equalizer",
                style = MaterialTheme.typography.titleLarge,
                color = VoxColors.Accent,
                modifier = Modifier.weight(1f),
            )
            QuietButton("Reset", onReset)
            QuietButton("Done", onDismiss)
        }
        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("Enable", style = MaterialTheme.typography.titleSmall, color = VoxColors.Text)
            Switch(
                checked = enabled,
                onCheckedChange = onEnable,
                colors = SwitchDefaults.colors(
                    checkedThumbColor = VoxColors.BgApp,
                    checkedTrackColor = VoxColors.Accent,
                    uncheckedThumbColor = VoxColors.TextMuted,
                    uncheckedTrackColor = VoxColors.BgPanel,
                ),
            )
        }
        Text(
            "AOSP Equalizer on this device — GrapheneOS may omit the effect. No GMS.",
            style = MaterialTheme.typography.bodySmall,
            color = VoxColors.TextMuted,
        )
        Row(
            Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            EqualizerControl.PRESETS.forEach { (id, label) ->
                EqPresetChip(
                    label = label,
                    selected = state.eqPreset == id,
                    preferred = state.eqPreferredId == id,
                    onSelect = { onPreset(id) },
                    onPin = { },
                )
            }
        }
        Text(
            "Preamp ${EqualizerControl.formatDb(state.eqPreampDb)}",
            style = MaterialTheme.typography.titleSmall,
            color = VoxColors.Text,
        )
        Slider(
            value = state.eqPreampDb,
            onValueChange = onPreamp,
            valueRange = EqualizerControl.PREAMP_MIN_DB..EqualizerControl.PREAMP_MAX_DB,
            enabled = enabled,
            colors = SliderDefaults.colors(
                thumbColor = VoxColors.Accent,
                activeTrackColor = VoxColors.Accent,
                inactiveTrackColor = VoxColors.BorderSoft,
            ),
        )
        Text("Bands", style = MaterialTheme.typography.titleSmall, color = VoxColors.Text)
        Row(
            Modifier
                .fillMaxWidth()
                .height(200.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.Bottom,
        ) {
            EqualizerControl.BAND_LABELS.forEachIndexed { index, label ->
                val gain = state.eqBandsDb.getOrElse(index) { 0f }
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                    modifier = Modifier.weight(1f),
                ) {
                    Text(
                        EqualizerControl.formatDb(gain),
                        style = MaterialTheme.typography.labelSmall,
                        color = VoxColors.Accent,
                        maxLines = 1,
                    )
                    Box(
                        Modifier
                            .height(140.dp)
                            .fillMaxWidth(),
                        contentAlignment = Alignment.Center,
                    ) {
                        Slider(
                            value = gain,
                            onValueChange = { onBand(index, it) },
                            valueRange = EqualizerControl.GAIN_MIN_DB..EqualizerControl.GAIN_MAX_DB,
                            enabled = enabled,
                            modifier = Modifier
                                .width(140.dp)
                                .graphicsLayer { rotationZ = -90f },
                            colors = SliderDefaults.colors(
                                thumbColor = VoxColors.Accent,
                                activeTrackColor = VoxColors.Accent,
                                inactiveTrackColor = VoxColors.BorderSoft,
                            ),
                        )
                    }
                    Text(
                        if (label.endsWith("kHz")) {
                            label.removeSuffix("kHz") + "k"
                        } else {
                            label.removeSuffix("Hz")
                        },
                        style = MaterialTheme.typography.labelSmall,
                        color = VoxColors.TextMuted,
                        maxLines = 1,
                    )
                }
            }
        }
        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(Modifier.weight(1f)) {
                Text("Snap bands", style = MaterialTheme.typography.titleSmall, color = VoxColors.Text)
                Text(
                    "Neighbor bands follow when you drag",
                    style = MaterialTheme.typography.bodySmall,
                    color = VoxColors.TextMuted,
                )
            }
            Switch(
                checked = state.eqSnapBands,
                onCheckedChange = onSnap,
                enabled = enabled,
                colors = SwitchDefaults.colors(
                    checkedThumbColor = VoxColors.BgApp,
                    checkedTrackColor = VoxColors.Accent,
                    uncheckedThumbColor = VoxColors.TextMuted,
                    uncheckedTrackColor = VoxColors.BgPanel,
                ),
            )
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun EqPresetChip(
    label: String,
    selected: Boolean,
    preferred: Boolean,
    onSelect: () -> Unit,
    onPin: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val haptics = LocalHapticFeedback.current
    val text = buildString {
        if (selected) append("✓ ")
        append(label)
        if (preferred) append(" ★")
    }
    Text(
        text,
        modifier
            .clip(VoxShapes.card)
            .background(
                when {
                    preferred -> VoxColors.AccentSoft
                    selected -> VoxColors.BgPanel
                    else -> VoxColors.BgElevated
                },
            )
            .border(
                1.dp,
                if (preferred) VoxColors.Accent else VoxColors.BorderSoft,
                VoxShapes.card,
            )
            .combinedClickable(
                onClick = onSelect,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onPin()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(label)
                    if (selected) append(", selected")
                    if (preferred) append(", preferred")
                    append(". Double-tap to apply. Long-press to pin or clear preferred.")
                }
            }
            .padding(horizontal = 8.dp, vertical = 10.dp),
        style = MaterialTheme.typography.bodyMedium,
        color = if (preferred || selected) VoxColors.Accent else VoxColors.Text,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
    )
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun AudioSinkRow(
    device: AudioRoute.Device,
    selected: Boolean,
    pinned: Boolean,
    onSelect: () -> Unit,
    onPin: () -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    val label = buildString {
        if (selected) append("✓ ")
        append(device.name)
        append(" · ")
        append(device.typeLabel)
        if (pinned) append(" · Preferred")
    }
    Text(
        label,
        Modifier
            .fillMaxWidth()
            .clip(VoxShapes.card)
            .background(
                when {
                    pinned -> VoxColors.AccentSoft
                    selected -> VoxColors.BgPanel
                    else -> VoxColors.BgElevated
                },
            )
            .border(
                1.dp,
                if (pinned) VoxColors.Accent else VoxColors.BorderSoft,
                VoxShapes.card,
            )
            .combinedClickable(
                onClick = onSelect,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onPin()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(device.name)
                    append(", ")
                    append(device.typeLabel)
                    if (selected) append(", selected")
                    if (pinned) append(", preferred")
                    append(". Double-tap to route. Long-press to pin or clear preferred.")
                }
            }
            .padding(horizontal = 12.dp, vertical = 8.dp),
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
        style = MaterialTheme.typography.bodyMedium,
        color = if (pinned || selected) VoxColors.Accent else VoxColors.Text,
    )
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun DlnaRendererRow(
    renderer: DlnaCastControl.Renderer,
    selected: Boolean,
    isDefault: Boolean,
    onSelect: () -> Unit,
    onSetDefault: () -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    val label = buildString {
        if (selected) append("✓ ")
        append(renderer.name)
        if (renderer.isTv) append(" · TV")
        append(" · ")
        append(renderer.address)
        if (isDefault) append(" · Default")
    }
    Text(
        label,
        Modifier
            .fillMaxWidth()
            .clip(VoxShapes.card)
            .background(
                when {
                    isDefault -> VoxColors.AccentSoft
                    selected -> VoxColors.BgPanel
                    else -> VoxColors.BgElevated
                },
            )
            .border(
                1.dp,
                if (isDefault) VoxColors.Accent else VoxColors.BorderSoft,
                VoxShapes.card,
            )
            .combinedClickable(
                onClick = onSelect,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onSetDefault()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(renderer.name)
                    if (renderer.isTv) append(", TV")
                    append(", ")
                    append(renderer.address)
                    if (selected) append(", selected")
                    if (isDefault) append(", default")
                    append(". Double-tap to select. Long-press to set or clear default.")
                }
            }
            .padding(horizontal = 10.dp, vertical = 8.dp),
        style = MaterialTheme.typography.bodySmall,
        color = if (isDefault || selected) VoxColors.Accent else VoxColors.Text,
    )
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun HomeFilterChip(
    label: String,
    selected: Boolean,
    preferred: Boolean,
    onSelect: () -> Unit,
    onPin: () -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    val text = buildString {
        append(label)
        if (preferred) append(" ★")
    }
    Text(
        text,
        Modifier
            .clip(VoxShapes.pill)
            .background(
                when {
                    preferred -> VoxColors.AccentSoft
                    selected -> VoxColors.AccentSoft
                    else -> VoxColors.BgElevated
                },
            )
            .border(
                1.dp,
                when {
                    preferred -> VoxColors.Accent
                    selected -> VoxColors.Accent
                    else -> VoxColors.BorderSoft
                },
                VoxShapes.pill,
            )
            .combinedClickable(
                onClick = onSelect,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onPin()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(label)
                    append(" filter")
                    if (selected) append(", selected")
                    if (preferred) append(", preferred")
                    append(". Double-tap to apply. Long-press to pin or clear preferred.")
                }
            }
            .padding(horizontal = 12.dp, vertical = 8.dp),
        style = MaterialTheme.typography.labelLarge,
        color = if (preferred || selected) VoxColors.Accent else VoxColors.TextSecondary,
        maxLines = 1,
    )
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun BookmarkRow(
    bookmark: BookmarkStore.Bookmark,
    onPlay: () -> Unit,
    onAddToList: () -> Unit,
    onRemove: () -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    Row(
        Modifier
            .fillMaxWidth()
            .clip(VoxShapes.card)
            .background(VoxColors.BgElevated)
            .combinedClickable(
                onClick = onPlay,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onAddToList()
                },
            )
            .semantics {
                contentDescription = buildString {
                    append(bookmark.title)
                    append(" at ")
                    append(fmtBookmarkPos(bookmark.positionMs))
                    append(". Double-tap to play. Long-press to add to a list.")
                }
            }
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                bookmark.title,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                fmtBookmarkPos(bookmark.positionMs),
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
            )
        }
        IconButton(onClick = onRemove, modifier = Modifier.size(36.dp)) {
            Icon(Icons.Default.Close, "Remove bookmark", tint = VoxColors.TextMuted)
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
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
    onAddToList: () -> Unit,
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
                    append(". Double-tap to play. Long-press to add to a list. Use drag handle or move buttons to reorder.")
                }
            }
            .combinedClickable(
                enabled = !dragging,
                onClick = onPlay,
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    onAddToList()
                },
            )
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
    var showCodecMatrix by remember { mutableStateOf(false) }
    val codecReport = remember { CodecFixtureMatrix.probe() }
    LazyColumn(
        Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        contentPadding = PaddingValues(top = 8.dp, bottom = 24.dp),
    ) {
        item {
            Text("More", style = MaterialTheme.typography.titleLarge, color = VoxColors.Accent)
        }
        item {
            MoreIconRow(
                icon = Icons.Default.Devices,
                title = if (state.remoteConnected) {
                    "Desktop · $linkLabel"
                } else {
                    "Connect desktop"
                },
                subtitle = if (state.remoteConnected) {
                    "v${state.remoteVersion.ifBlank { "?" }} · ${state.remoteTitle.ifBlank { "idle" }}"
                } else {
                    "Pair Wi‑Fi or Bluetooth — no cloud"
                },
                accent = state.remoteConnected,
                onClick = { vm.openConnect(true) },
            )
        }
        if (state.remoteConnected) {
            item {
                Text(
                    "${state.remotePositionLabel} · vol ${state.remoteVolume}%",
                    style = MaterialTheme.typography.bodySmall,
                    color = VoxColors.TextMuted,
                )
            }
            item {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    MoreIconChip(Icons.Default.SkipPrevious, "Prev", vm::remotePrev, Modifier.weight(1f))
                    MoreIconChip(
                        if (state.remotePlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                        if (state.remotePlaying) "Pause" else "Play",
                        vm::remotePlayPause,
                        Modifier.weight(1f),
                        filled = true,
                    )
                    MoreIconChip(Icons.Default.SkipNext, "Next", vm::remoteNext, Modifier.weight(1f))
                }
            }
            item {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    MoreIconChip(Icons.Default.Stop, "Stop", vm::remoteStop, Modifier.weight(1f))
                    MoreIconChip(Icons.Default.Replay, "−5s", vm::remoteSeekBack, Modifier.weight(1f))
                    MoreIconChip(Icons.Default.Forward5, "+5s", vm::remoteSeekFwd, Modifier.weight(1f))
                    MoreIconChip(Icons.Default.VolumeOff, "Vol −", vm::remoteVolDown, Modifier.weight(1f))
                    MoreIconChip(Icons.Default.VolumeUp, "Vol +", vm::remoteVolUp, Modifier.weight(1f))
                }
            }
            item {
                MoreIconRow(
                    icon = Icons.Default.Sync,
                    title = if (state.syncBusy) "Syncing…" else "Sync playlists & podcasts",
                    subtitle = state.syncMessage.ifBlank { "Pull from connected desktop" },
                    onClick = vm::syncFromDesktop,
                    enabled = !state.syncBusy,
                )
            }
        }
        item {
            Text("Appearance", style = MaterialTheme.typography.titleSmall, color = VoxColors.Accent)
        }
        item {
            Row(
                Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                listOf(
                    ThemeMode.Dark to "Dark",
                    ThemeMode.Light to "Light",
                    ThemeMode.System to "System",
                ).forEach { (mode, label) ->
                    ThemeModeChip(
                        label = label,
                        selected = state.themeMode == mode,
                        preferred = state.themePreferred == mode,
                        onSelect = { vm.setThemeMode(mode) },
                        onPin = { vm.setPreferredThemeMode(mode) },
                    )
                }
            }
        }
        item {
            Text("Player", style = MaterialTheme.typography.titleSmall, color = VoxColors.Accent)
        }
        item {
            MoreIconRow(
                icon = Icons.Default.Settings,
                title = "Player settings",
                subtitle = "Quality, captions, sleep, lock",
                onClick = { vm.openPlayerSheet(PlayerSheet.Settings) },
            )
        }
        item {
            MoreIconRow(
                icon = Icons.Default.Speed,
                title = "Playback speed",
                subtitle = "0.25× – 3.0×",
                onClick = { vm.openPlayerSheet(PlayerSheet.Speed) },
            )
        }
        item {
            MoreIconRow(
                icon = Icons.Default.Storage,
                title = "Downloads and storage",
                subtitle = "Cache and on-device files",
                onClick = { vm.openPlayerSheet(PlayerSheet.Storage) },
            )
        }
        item {
            MoreIconRow(
                icon = Icons.Default.Cast,
                title = if (state.dlnaEnabled) "Cast (DLNA)" else "Cast to TV",
                subtitle = state.dlnaMessage.ifBlank {
                    if (state.dlnaEnabled) "Scan LAN MediaRenderers" else "FOSS DLNA — no Google Cast"
                },
                accent = state.dlnaEnabled,
                onClick = vm::castFromNowPlaying,
            )
        }
        item {
            MoreIconRow(
                icon = Icons.Default.Bookmark,
                title = "Favorites",
                subtitle = if (state.bookmarks.isEmpty()) {
                    "Open list · save from Now Playing"
                } else {
                    "${state.bookmarks.size} saved · tap to open"
                },
                onClick = { vm.openPlayerSheet(PlayerSheet.Favorites) },
            )
        }
        item {
            MoreIconRow(
                icon = Icons.Default.Timer,
                title = "Sleep timer",
                subtitle = state.sleepRemainingLabel.ifBlank { "Fade out then pause" },
                onClick = { vm.openPlayerSheet(PlayerSheet.Sleep) },
            )
        }
        item {
            MoreIconRow(
                icon = Icons.Default.Memory,
                title = if (showCodecMatrix) "Hide codec matrix" else "Codec fixture matrix",
                subtitle = "On-device MediaCodec probe",
                onClick = { showCodecMatrix = !showCodecMatrix },
            )
        }
        if (showCodecMatrix) {
            item {
                Text(
                    codecReport.asText(),
                    style = MaterialTheme.typography.bodySmall,
                    color = VoxColors.TextSecondary,
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(VoxShapes.card)
                        .background(VoxColors.BgElevated)
                        .padding(10.dp),
                )
            }
        }
        item {
            Text("Help", style = MaterialTheme.typography.titleSmall, color = VoxColors.Accent)
        }
        item {
            MoreIconRow(
                icon = Icons.Default.Info,
                title = "About / Help",
                subtitle = "v${BuildConfig.VERSION_NAME} · docs & updates",
                onClick = { vm.openPlayerSheet(PlayerSheet.About) },
            )
        }
        item {
            MoreIconRow(
                icon = Icons.Default.Policy,
                title = "Codec policy",
                subtitle = "FOSS / MediaCodec only — no in-tree x264/x265",
                onClick = { vm.openPlayerSheet(PlayerSheet.CodecPolicy) },
            )
        }
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
        if (state.remoteConnected && state.remoteLibrary.isNotEmpty()) {
            item { Text("Desktop library", style = MaterialTheme.typography.titleMedium) }
            items(state.remoteLibrary.take(if (wide) 120 else 60)) { item ->
                LibraryRow(item.title) { vm.remoteOpen(item.path) }
            }
        }
        if (state.dlnaEnabled && state.dlnaRenderers.isNotEmpty()) {
            item {
                Text("Cast targets", style = MaterialTheme.typography.titleSmall, color = VoxColors.Accent)
            }
            items(state.dlnaRenderers, key = { it.id }) { r ->
                DlnaRendererRow(
                    renderer = r,
                    selected = state.dlnaSelectedId == r.id,
                    isDefault = state.dlnaDefaultId == r.id,
                    onSelect = { vm.selectDlnaRenderer(r.id) },
                    onSetDefault = { vm.setDlnaDefaultRenderer(r.id) },
                )
            }
        }
    }
}

@Composable
private fun MoreIconRow(
    icon: ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    accent: Boolean = false,
    enabled: Boolean = true,
) {
    Row(
        modifier
            .fillMaxWidth()
            .clip(VoxShapes.card)
            .background(if (accent) VoxColors.AccentSoft else VoxColors.BgElevated)
            .clickable(enabled = enabled, onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Box(
            Modifier
                .size(40.dp)
                .clip(CircleShape)
                .background(if (accent) VoxColors.Accent.copy(alpha = 0.2f) else VoxColors.BgHover),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                icon,
                contentDescription = title,
                tint = if (accent) VoxColors.Accent else VoxColors.TextSecondary,
                modifier = Modifier.size(22.dp),
            )
        }
        Column(Modifier.weight(1f)) {
            Text(
                title,
                style = MaterialTheme.typography.titleSmall,
                color = if (enabled) VoxColors.Text else VoxColors.TextMuted,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            if (subtitle.isNotBlank()) {
                Text(
                    subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = VoxColors.TextMuted,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun MoreIconChip(
    icon: ImageVector,
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    filled: Boolean = false,
) {
    Column(
        modifier
            .clip(VoxShapes.pill)
            .background(if (filled) VoxColors.Accent else VoxColors.BgElevated)
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Icon(
            icon,
            contentDescription = label,
            tint = if (filled) VoxColors.BgApp else VoxColors.Text,
            modifier = Modifier.size(22.dp),
        )
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            color = if (filled) VoxColors.BgApp else VoxColors.TextSecondary,
            maxLines = 1,
        )
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
        IconButton(onClick = onConnect) {
            Icon(
                Icons.Default.Devices,
                contentDescription = "Connect desktop",
                tint = if (state.activeOutput.startsWith("Desktop")) VoxColors.Success else VoxColors.Accent,
            )
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
fun SeekScrubber(
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
