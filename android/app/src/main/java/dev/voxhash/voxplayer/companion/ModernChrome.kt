package dev.voxhash.voxplayer.companion

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.ClosedCaption
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Headset
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Policy
import androidx.compose.material.icons.filled.QueueMusic
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material.icons.filled.RepeatOne
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material.icons.filled.Subtitles
import androidx.compose.material.icons.filled.Timer
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material.icons.filled.Update
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material.icons.filled.VolumeOff
import androidx.compose.material.icons.filled.WbTwilight
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.round

/**
 * Modern player chrome adapted from contemporary streaming UX —
 * FOSS / GrapheneOS / Quest honest: local files, Media3, no GMS YouTube.
 */
enum class PlayerSheet {
    None,
    Settings,
    Speed,
    Captions,
    More,
    Quality,
    TrackActions,
    Storage,
    Queue,
    Favorites,
    Sleep,
    About,
    CodecPolicy,
}

@Composable
fun SheetHandle() {
    Box(
        Modifier
            .fillMaxWidth()
            .padding(top = 8.dp, bottom = 4.dp),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            Modifier
                .width(36.dp)
                .height(4.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(VoxColors.BorderSoft),
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ModernPlayerSheets(
    state: PlayerUiState,
    onDismiss: () -> Unit,
    onOpenSheet: (PlayerSheet) -> Unit,
    onSpeed: (Float) -> Unit,
    onNudgeSpeed: (Float) -> Unit,
    onCaptionsOff: () -> Unit,
    onCaptionsLyrics: () -> Unit,
    onShowWhenMuted: (Boolean) -> Unit,
    onLoopVideo: (Boolean) -> Unit,
    onAmbient: (Boolean) -> Unit,
    onLockScreen: (Boolean) -> Unit,
    onOpenSleep: () -> Unit,
    onQualityMode: (String) -> Unit,
    onPlayNext: () -> Unit,
    onSavePlaylist: () -> Unit,
    onShare: () -> Unit,
    onAddQueue: () -> Unit,
    onOpenStorage: () -> Unit,
    onClearCache: () -> Unit,
    onShowDeviceFiles: (Boolean) -> Unit,
    onPlayQueueIndex: (Int) -> Unit = {},
    onRemoveQueueIndex: (Int) -> Unit = {},
    onPlayBookmark: (BookmarkStore.Bookmark) -> Unit = {},
    onRemoveBookmark: (String) -> Unit = {},
    onBookmarkNow: () -> Unit = {},
    onSleepMinutes: (Int) -> Unit = {},
    onClearSleep: () -> Unit = {},
    onOpenDocs: () -> Unit = {},
    onOpenReleases: () -> Unit = {},
    appVersionLabel: String = "",
) {
    // One ModalBottomSheet for all player menus. Swapping nested composables (Settings → Speed)
    // must not dispose the sheet — disposal fires onDismissRequest and clears the next sheet.
    if (state.playerSheet == PlayerSheet.None) return
    VoxSheet(onDismiss) {
        when (state.playerSheet) {
            PlayerSheet.None -> Unit
            PlayerSheet.Settings -> PlayerSettingsSheet(
                state = state,
                onQuality = { onOpenSheet(PlayerSheet.Quality) },
                onSpeed = { onOpenSheet(PlayerSheet.Speed) },
                onCaptions = { onOpenSheet(PlayerSheet.Captions) },
                onLock = { onLockScreen(!state.screenLocked) },
                onMore = { onOpenSheet(PlayerSheet.More) },
            )
            PlayerSheet.Speed -> PlaybackSpeedSheet(
                speed = state.playbackSpeed,
                onSpeed = onSpeed,
                onNudge = onNudgeSpeed,
            )
            PlayerSheet.Captions -> CaptionsSheet(
                state = state,
                onOff = onCaptionsOff,
                onLyrics = onCaptionsLyrics,
                onShowWhenMuted = onShowWhenMuted,
            )
            PlayerSheet.More -> MorePlayerSheet(
                state = state,
                onLoop = onLoopVideo,
                onAmbient = onAmbient,
                onSleep = onOpenSleep,
                onStorage = onOpenStorage,
            )
            PlayerSheet.Quality -> QualitySheet(
                mode = state.qualityMode,
                onSelect = onQualityMode,
            )
            PlayerSheet.TrackActions -> TrackActionsSheet(
                state = state,
                onDismiss = onDismiss,
                onPlayNext = onPlayNext,
                onSavePlaylist = onSavePlaylist,
                onShare = onShare,
                onAddQueue = onAddQueue,
            )
            PlayerSheet.Storage -> StorageSheet(
                state = state,
                onShowDeviceFiles = onShowDeviceFiles,
                onClearCache = onClearCache,
                onQualityAudio = { onQualityMode("audio") },
                onQualityAuto = { onQualityMode("auto") },
            )
            PlayerSheet.Queue -> QueueSheet(
                state = state,
                onPlayIndex = onPlayQueueIndex,
                onRemoveIndex = onRemoveQueueIndex,
            )
            PlayerSheet.Favorites -> FavoritesSheet(
                state = state,
                onPlay = onPlayBookmark,
                onRemove = onRemoveBookmark,
                onSaveNow = onBookmarkNow,
            )
            PlayerSheet.Sleep -> SleepSheet(
                state = state,
                onMinutes = onSleepMinutes,
                onClear = onClearSleep,
            )
            PlayerSheet.About -> AboutSheet(
                versionLabel = appVersionLabel,
                onOpenDocs = onOpenDocs,
                onOpenReleases = onOpenReleases,
                onCodecPolicy = { onOpenSheet(PlayerSheet.CodecPolicy) },
            )
            PlayerSheet.CodecPolicy -> CodecPolicySheet()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun VoxSheet(onDismiss: () -> Unit, content: @Composable () -> Unit) {
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = VoxColors.BgElevated,
        tonalElevation = 0.dp,
        dragHandle = { SheetHandle() },
    ) {
        content()
        Spacer(Modifier.height(28.dp))
    }
}

@Composable
private fun PlayerSettingsSheet(
    state: PlayerUiState,
    onQuality: () -> Unit,
    onSpeed: () -> Unit,
    onCaptions: () -> Unit,
    onLock: () -> Unit,
    onMore: () -> Unit,
) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 8.dp)) {
        SheetRow(Icons.Default.Tune, "Quality", state.qualityModeLabel()) { onQuality() }
        SheetRow(Icons.Default.Speed, "Playback speed", PlaybackSpeed.label(state.playbackSpeed)) { onSpeed() }
        SheetRow(Icons.Default.ClosedCaption, "Captions", state.captionsLabel()) { onCaptions() }
        SheetRow(
            Icons.Default.Lock,
            "Lock player controls",
            if (state.screenLocked) "On" else "Off",
        ) { onLock() }
        SheetRow(Icons.Default.Settings, "More", "") { onMore() }
    }
}

@Composable
private fun PlaybackSpeedSheet(
    speed: Float,
    onSpeed: (Float) -> Unit,
    onNudge: (Float) -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
            Text(
                String.format("%.2fx", speed),
                style = MaterialTheme.typography.headlineMedium,
                color = VoxColors.Text,
                fontWeight = FontWeight.SemiBold,
            )
            Row(
                Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                IconButton(
                    onClick = { onNudge(-0.05f) },
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(VoxColors.BgHover),
                ) {
                    Icon(Icons.Default.Remove, contentDescription = "Slower", tint = VoxColors.Text)
                }
                Slider(
                    value = speed.coerceIn(PlaybackSpeed.MIN, PlaybackSpeed.MAX),
                    onValueChange = onSpeed,
                    valueRange = PlaybackSpeed.MIN..PlaybackSpeed.MAX,
                    modifier = Modifier.weight(1f),
                    colors = SliderDefaults.colors(
                        thumbColor = VoxColors.Text,
                        activeTrackColor = VoxColors.Text,
                        inactiveTrackColor = VoxColors.BorderSoft,
                    ),
                )
                IconButton(
                    onClick = { onNudge(0.05f) },
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(VoxColors.BgHover),
                ) {
                    Icon(Icons.Default.Add, contentDescription = "Faster", tint = VoxColors.Text)
                }
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                PlaybackSpeed.PRESETS.forEach { preset ->
                    val selected = kotlin.math.abs(speed - preset) < 0.03f
                    Column(
                        Modifier.weight(1f),
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Box(
                            Modifier
                                .fillMaxWidth()
                                .height(40.dp)
                                .clip(RoundedCornerShape(20.dp))
                                .background(if (selected) VoxColors.Text else VoxColors.BgHover)
                                .clickable { onSpeed(preset) },
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                if (preset == 1.0f) "1.0" else preset.toString(),
                                color = if (selected) VoxColors.BgApp else VoxColors.Text,
                                fontWeight = FontWeight.Medium,
                                fontSize = 14.sp,
                            )
                        }
                        if (preset == 1.0f) {
                            Text("Normal", color = VoxColors.TextMuted, fontSize = 11.sp)
                        }
                    }
                }
            }
    }
}

@Composable
private fun CaptionsSheet(
    state: PlayerUiState,
    onOff: () -> Unit,
    onLyrics: () -> Unit,
    onShowWhenMuted: (Boolean) -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .verticalScroll(rememberScrollState()),
    ) {
            Text("Captions / lyrics", style = MaterialTheme.typography.titleLarge, color = VoxColors.Text)
            Spacer(Modifier.height(12.dp))
            SelectRow("Turn off captions", state.captionsMode == CaptionsMode.Off, onClick = onOff)
            SelectRow(
                "Sidecar lyrics / timed text",
                state.captionsMode == CaptionsMode.Lyrics,
                onClick = onLyrics,
            )
            HorizontalDivider(Modifier.padding(vertical = 12.dp), color = VoxColors.BorderSoft)
            Row(
                Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Default.VolumeOff, null, tint = VoxColors.TextSecondary)
                Spacer(Modifier.width(12.dp))
                Text("Show when muted", Modifier.weight(1f), color = VoxColors.Text)
                Switch(
                    checked = state.captionsShowWhenMuted,
                    onCheckedChange = onShowWhenMuted,
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = VoxColors.BgApp,
                        checkedTrackColor = VoxColors.Accent,
                    ),
                )
            }
            Text(
                "Place a .lrc / .srt / .vtt / .txt next to the media file (same folder + base name). No cloud captions. GrapheneOS system caption prefs stay separate.",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
                modifier = Modifier.padding(top = 12.dp),
            )
            if (state.captionsMode == CaptionsMode.Lyrics) {
                Spacer(Modifier.height(16.dp))
                Text(
                    if (state.lyricsSource.isNotBlank()) "Loaded · ${state.lyricsSource}" else "No sidecar found for this file",
                    style = MaterialTheme.typography.titleSmall,
                    color = VoxColors.Accent,
                )
                Spacer(Modifier.height(8.dp))
                if (state.lyricsLines.isEmpty()) {
                    Text(
                        "Expected e.g. Song.mp3 + Song.lrc, or Video.mp4 + Video.srt on the same path / SAF folder.",
                        style = MaterialTheme.typography.bodySmall,
                        color = VoxColors.TextSecondary,
                    )
                } else {
                    state.lyricsLines.forEachIndexed { i, line ->
                        val active = i == state.lyricsActiveIndex
                        Text(
                            line,
                            color = if (active) VoxColors.Accent else VoxColors.TextSecondary,
                            fontWeight = if (active) FontWeight.SemiBold else FontWeight.Normal,
                            fontSize = if (active) 16.sp else 14.sp,
                            modifier = Modifier.padding(vertical = 3.dp),
                        )
                    }
                }
            }
    }
}

@Composable
private fun MorePlayerSheet(
    state: PlayerUiState,
    onLoop: (Boolean) -> Unit,
    onAmbient: (Boolean) -> Unit,
    onSleep: () -> Unit,
    onStorage: () -> Unit,
) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 8.dp)) {
            ToggleRow(Icons.Default.RepeatOne, "Loop video", state.loopVideo, onLoop)
            ToggleRow(Icons.Default.WbTwilight, "Ambient mode", state.ambientMode, onAmbient)
            SheetRow(
                Icons.Default.Timer,
                "Sleep timer",
                state.sleepRemainingLabel,
            ) { onSleep() }
            SheetRow(Icons.Default.Storage, "Downloads and storage", "") { onStorage() }
            SheetRow(
                Icons.Default.Videocam,
                "Quest / panel tips",
                "2D panel · PiP when available",
            ) { }
            Text(
                "No YouTube Music / GMS links. DLNA cast lives under Now Playing output.",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            )
    }
}

@Composable
private fun QualitySheet(
    mode: String,
    onSelect: (String) -> Unit,
) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
            Text(
                "Quality for current media",
                style = MaterialTheme.typography.titleMedium,
                color = VoxColors.Text,
            )
            Spacer(Modifier.height(8.dp))
            SelectRow("Auto (native)", mode == "auto", "Play the file as stored") {
                onSelect("auto")
            }
            SelectRow(
                "Prefer higher detail",
                mode == "high",
                "Hint Media3 for larger surfaces (local files)",
            ) {
                onSelect("high")
            }
            SelectRow(
                "Data / battery saver",
                mode == "saver",
                "Lower surface / skip ambient glow",
            ) {
                onSelect("saver")
            }
            SelectRow(
                "Audio only if video",
                mode == "audio",
                "Hide video surface; keep Media3 audio",
            ) {
                onSelect("audio")
            }
            Text(
                "Local library has no adaptive CDN rungs — these are player preferences, not YouTube qualities.",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
                modifier = Modifier.padding(top = 12.dp),
            )
    }
}

@Composable
private fun TrackActionsSheet(
    state: PlayerUiState,
    onDismiss: () -> Unit,
    onPlayNext: () -> Unit,
    onSavePlaylist: () -> Unit,
    onShare: () -> Unit,
    onAddQueue: () -> Unit,
) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(
                        state.localTitle.ifBlank { "Now Playing" },
                        style = MaterialTheme.typography.titleMedium,
                        color = VoxColors.Text,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        state.localPositionLabel,
                        style = MaterialTheme.typography.bodySmall,
                        color = VoxColors.TextMuted,
                    )
                }
                IconButton(onClick = onDismiss) {
                    Icon(Icons.Default.Close, contentDescription = "Close", tint = VoxColors.TextMuted)
                }
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                QuickAction("Play next", Icons.Default.QueueMusic, Modifier.weight(1f), onPlayNext)
                QuickAction("Save to list", Icons.Default.Add, Modifier.weight(1f), onSavePlaylist)
                QuickAction("Share", Icons.Default.Share, Modifier.weight(1f), onShare)
            }
            Spacer(Modifier.height(8.dp))
            SheetRow(Icons.Default.QueueMusic, "Add to queue", "") { onAddQueue(); onDismiss() }
            SheetRow(Icons.Default.MusicNote, "Go to artist / album", "Browse Audio facets") { onDismiss() }
    }
}

@Composable
private fun StorageSheet(
    state: PlayerUiState,
    onShowDeviceFiles: (Boolean) -> Unit,
    onClearCache: () -> Unit,
    onQualityAudio: () -> Unit,
    onQualityAuto: () -> Unit,
) {
    Column(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            Text("Downloads and storage", style = MaterialTheme.typography.titleLarge, color = VoxColors.Text)
            Spacer(Modifier.height(12.dp))
            Text("Cache", color = VoxColors.TextMuted, style = MaterialTheme.typography.labelLarge)
            Text(
                state.cacheUsageLabel.ifBlank { "Artwork + share cards under app cache" },
                color = VoxColors.TextSecondary,
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(8.dp))
            Box(
                Modifier
                    .fillMaxWidth()
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(VoxColors.BorderSoft),
            ) {
                Box(
                    Modifier
                        .fillMaxWidth(fraction = state.cacheUsageFraction.coerceIn(0.02f, 1f))
                        .height(4.dp)
                        .background(VoxColors.Accent),
                )
            }
            Spacer(Modifier.height(16.dp))
            ToggleRow(
                Icons.Default.Headset,
                "Show device files",
                state.showDeviceFiles,
                onShowDeviceFiles,
                sub = "Show all audio/video from MediaStore",
            )
            SheetRow(
                Icons.Default.MusicNote,
                "Audio preference",
                if (state.qualityMode == "audio") "Audio only if video" else "Normal",
            ) {
                if (state.qualityMode == "audio") onQualityAuto() else onQualityAudio()
            }
            SheetRow(Icons.Default.Storage, "Clear artwork / share cache", "") { onClearCache() }
            Text(
                "Offline-first: no cloud downloads. Wi‑Fi-only toggles apply when you add a download manager later.",
                style = MaterialTheme.typography.bodySmall,
                color = VoxColors.TextMuted,
                modifier = Modifier.padding(vertical = 12.dp),
            )
    }
}

@Composable
private fun QuickAction(label: String, icon: ImageVector, modifier: Modifier, onClick: () -> Unit) {
    Column(
        modifier
            .clip(RoundedCornerShape(14.dp))
            .background(VoxColors.BgHover)
            .clickable(onClick = onClick)
            .padding(vertical = 14.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(icon, contentDescription = label, tint = VoxColors.Text)
        Spacer(Modifier.height(6.dp))
        Text(label, color = VoxColors.Text, fontSize = 12.sp)
    }
}

@Composable
private fun SheetRow(
    icon: ImageVector,
    title: String,
    trailing: String,
    onClick: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, contentDescription = null, tint = VoxColors.Text)
        Spacer(Modifier.width(16.dp))
        Text(title, Modifier.weight(1f), color = VoxColors.Text, style = MaterialTheme.typography.bodyLarge)
        if (trailing.isNotBlank()) {
            Text(trailing, color = VoxColors.TextMuted, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.width(4.dp))
            Text("›", color = VoxColors.TextMuted)
        }
    }
}

@Composable
private fun ToggleRow(
    icon: ImageVector,
    title: String,
    checked: Boolean,
    onChecked: (Boolean) -> Unit,
    sub: String = "",
) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, contentDescription = null, tint = VoxColors.Text)
        Spacer(Modifier.width(16.dp))
        Column(Modifier.weight(1f)) {
            Text(title, color = VoxColors.Text, style = MaterialTheme.typography.bodyLarge)
            if (sub.isNotBlank()) {
                Text(sub, color = VoxColors.TextMuted, style = MaterialTheme.typography.bodySmall)
            }
        }
        Switch(
            checked = checked,
            onCheckedChange = onChecked,
            colors = SwitchDefaults.colors(
                checkedThumbColor = VoxColors.BgApp,
                checkedTrackColor = VoxColors.Accent,
            ),
        )
    }
}

@Composable
private fun SelectRow(
    title: String,
    selected: Boolean,
    sub: String = "",
    onClick: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .clickable(onClick = onClick)
            .padding(vertical = 12.dp, horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            if (selected) "✓" else " ",
            Modifier.width(28.dp),
            color = VoxColors.Accent,
            fontWeight = FontWeight.Bold,
        )
        Column {
            Text(title, color = VoxColors.Text, style = MaterialTheme.typography.bodyLarge)
            if (sub.isNotBlank()) {
                Text(sub, color = VoxColors.TextMuted, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
fun MiniPlayerBar(
    state: PlayerUiState,
    onPlayPause: () -> Unit,
    onOpenNowPlaying: () -> Unit,
    onOpenSettings: () -> Unit,
) {
    if (state.localTitle.isBlank() && !state.localPlaying && state.localPositionMs <= 0L) return
    Row(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 10.dp, vertical = 4.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(VoxColors.BgElevated)
            .clickable(onClick = onOpenNowPlaying)
            .padding(horizontal = 10.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier
                .size(40.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(VoxColors.AccentSoft),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                if (state.localIsVideo) Icons.Default.Videocam else Icons.Default.MusicNote,
                contentDescription = null,
                tint = VoxColors.Accent,
            )
        }
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(
                state.localTitle.ifBlank { "Ready" },
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                color = VoxColors.Text,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium,
            )
            Text(
                state.localPositionLabel,
                maxLines = 1,
                color = VoxColors.TextMuted,
                style = MaterialTheme.typography.labelSmall,
            )
        }
        IconButton(onClick = onOpenSettings) {
            Icon(Icons.Default.MoreHoriz, contentDescription = "Player settings", tint = VoxColors.TextSecondary)
        }
        IconButton(onClick = onPlayPause) {
            Icon(
                if (state.localPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                contentDescription = if (state.localPlaying) "Pause" else "Play",
                tint = VoxColors.Text,
            )
        }
    }
}

@Composable
fun VideoTopChrome(
    captionsOn: Boolean,
    onCaptions: () -> Unit,
    onSettings: () -> Unit,
    locked: Boolean,
) {
    if (locked) return
    Row(
        Modifier
            .fillMaxWidth()
            .padding(8.dp),
        horizontalArrangement = Arrangement.End,
    ) {
        Box(
            Modifier
                .size(44.dp)
                .clip(CircleShape)
                .background(VoxColors.BgApp.copy(alpha = 0.55f))
                .clickable(onClick = onCaptions),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.Default.Subtitles,
                contentDescription = "Captions",
                tint = if (captionsOn) VoxColors.Accent else VoxColors.Text,
            )
        }
        Spacer(Modifier.width(8.dp))
        Box(
            Modifier
                .size(44.dp)
                .clip(CircleShape)
                .background(VoxColors.BgApp.copy(alpha = 0.55f))
                .clickable(onClick = onSettings),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Default.Settings, contentDescription = "Settings", tint = VoxColors.Text)
        }
    }
}

@Composable
private fun QueueSheet(
    state: PlayerUiState,
    onPlayIndex: (Int) -> Unit,
    onRemoveIndex: (Int) -> Unit,
) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
        Text("Up next", style = MaterialTheme.typography.titleLarge, color = VoxColors.Text)
        Text(
            if (state.localQueue.isEmpty()) "Queue is empty — play from Video or Audio"
            else "${state.localQueueIndex + 1} / ${state.localQueue.size}",
            style = MaterialTheme.typography.bodySmall,
            color = VoxColors.TextMuted,
            modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
        )
        state.localQueue.take(80).forEach { row ->
            Row(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(10.dp))
                    .background(if (row.isCurrent) VoxColors.AccentSoft else VoxColors.BgHover)
                    .clickable { onPlayIndex(row.index) }
                    .padding(horizontal = 12.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        row.title,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        color = VoxColors.Text,
                        fontWeight = if (row.isCurrent) FontWeight.SemiBold else FontWeight.Normal,
                    )
                    if (row.artist.isNotBlank()) {
                        Text(row.artist, maxLines = 1, color = VoxColors.TextMuted, fontSize = 12.sp)
                    }
                }
                if (!row.isCurrent) {
                    IconButton(onClick = { onRemoveIndex(row.index) }) {
                        Icon(Icons.Default.Close, "Remove from queue", tint = VoxColors.TextMuted)
                    }
                }
            }
            Spacer(Modifier.height(4.dp))
        }
    }
}

@Composable
private fun FavoritesSheet(
    state: PlayerUiState,
    onPlay: (BookmarkStore.Bookmark) -> Unit,
    onRemove: (String) -> Unit,
    onSaveNow: () -> Unit,
) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
        Text("Favorites", style = MaterialTheme.typography.titleLarge, color = VoxColors.Text)
        Text(
            "Saved positions from Now Playing, notification Favorite, or Save here. Also under Lists → Favorites.",
            style = MaterialTheme.typography.bodySmall,
            color = VoxColors.TextMuted,
            modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
        )
        SheetRow(Icons.Default.Bookmark, "Save current position", state.localTitle.ifBlank { "Nothing playing" }) {
            onSaveNow()
        }
        Spacer(Modifier.height(8.dp))
        if (state.bookmarks.isEmpty()) {
            Text(
                "No favorites yet — tap the bookmark on Now Playing or Save current position.",
                style = MaterialTheme.typography.bodyMedium,
                color = VoxColors.TextSecondary,
            )
        } else {
            state.bookmarks.forEach { bm ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(10.dp))
                        .background(VoxColors.BgHover)
                        .clickable { onPlay(bm) }
                        .padding(horizontal = 12.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(bm.title, maxLines = 1, overflow = TextOverflow.Ellipsis, color = VoxColors.Text)
                        Text(
                            formatBookmarkPos(bm.positionMs) + if (bm.isVideo) " · video" else " · audio",
                            color = VoxColors.TextMuted,
                            fontSize = 12.sp,
                        )
                    }
                    IconButton(onClick = { onRemove(bm.uri) }) {
                        Icon(Icons.Default.Close, "Remove favorite", tint = VoxColors.TextMuted)
                    }
                }
                Spacer(Modifier.height(4.dp))
            }
        }
    }
}

@Composable
private fun SleepSheet(
    state: PlayerUiState,
    onMinutes: (Int) -> Unit,
    onClear: () -> Unit,
) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
        Text("Sleep timer", style = MaterialTheme.typography.titleLarge, color = VoxColors.Text)
        Text(
            state.sleepRemainingLabel.ifBlank { "Off — fades out then pauses" },
            style = MaterialTheme.typography.bodySmall,
            color = VoxColors.TextMuted,
            modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
        )
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SleepTimer.DURATIONS_MIN.take(3).forEach { m ->
                Box(
                    Modifier
                        .weight(1f)
                        .height(44.dp)
                        .clip(RoundedCornerShape(22.dp))
                        .background(VoxColors.BgHover)
                        .clickable { onMinutes(m) },
                    contentAlignment = Alignment.Center,
                ) {
                    Text("${m}m", color = VoxColors.Text, fontWeight = FontWeight.Medium)
                }
            }
        }
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SleepTimer.DURATIONS_MIN.drop(3).forEach { m ->
                Box(
                    Modifier
                        .weight(1f)
                        .height(44.dp)
                        .clip(RoundedCornerShape(22.dp))
                        .background(VoxColors.BgHover)
                        .clickable { onMinutes(m) },
                    contentAlignment = Alignment.Center,
                ) {
                    Text("${m}m", color = VoxColors.Text, fontWeight = FontWeight.Medium)
                }
            }
            Box(
                Modifier
                    .weight(1f)
                    .height(44.dp)
                    .clip(RoundedCornerShape(22.dp))
                    .background(VoxColors.BgHover)
                    .clickable(onClick = onClear),
                contentAlignment = Alignment.Center,
            ) {
                Text("Off", color = VoxColors.Text, fontWeight = FontWeight.Medium)
            }
        }
    }
}

@Composable
private fun AboutSheet(
    versionLabel: String,
    onOpenDocs: () -> Unit,
    onOpenReleases: () -> Unit,
    onCodecPolicy: () -> Unit,
) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 8.dp)) {
        Text(
            "About VoxPlayer",
            style = MaterialTheme.typography.titleLarge,
            color = VoxColors.Text,
            modifier = Modifier.padding(horizontal = 16.dp),
        )
        Text(
            "v$versionLabel · FOSS Media3 · no GMS\nGrapheneOS-honest local playback · contact@voxhash.dev",
            style = MaterialTheme.typography.bodySmall,
            color = VoxColors.TextMuted,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
        )
        SheetRow(Icons.Default.Info, "Help / docs (browser)", "GitHub README") { onOpenDocs() }
        SheetRow(Icons.Default.Update, "Check for updates (browser)", "GitHub Releases") { onOpenReleases() }
        SheetRow(Icons.Default.Policy, "Codec policy", "Wrap FOSS / MediaCodec only") { onCodecPolicy() }
        Text(
            "Prefer Obtainium or verified APKs from GitHub Releases. No silent auto-install.",
            style = MaterialTheme.typography.bodySmall,
            color = VoxColors.TextMuted,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
        )
    }
}

@Composable
private fun CodecPolicySheet() {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .verticalScroll(rememberScrollState()),
    ) {
        Text("Codec policy", style = MaterialTheme.typography.titleLarge, color = VoxColors.Text)
        Spacer(Modifier.height(12.dp))
        Text(
            "VoxPlayer does not vendor in-tree H.264/x264 or H.265/x265 source. Android / Quest / GrapheneOS decode goes through Media3 → MediaCodec (device firmware). Desktop wraps system FOSS (libav / libvlc). Probe this device under More → Codec fixture matrix.",
            style = MaterialTheme.typography.bodyMedium,
            color = VoxColors.TextSecondary,
        )
    }
}

private fun formatBookmarkPos(ms: Long): String {
    val totalSec = (ms / 1000L).coerceAtLeast(0L)
    val m = totalSec / 60L
    val s = totalSec % 60L
    return "%d:%02d".format(m, s)
}

enum class CaptionsMode { Off, Lyrics }

fun PlayerUiState.qualityModeLabel(): String = when (qualityMode) {
    "high" -> "Higher detail ›"
    "saver" -> "Data saver ›"
    "audio" -> "Audio only ›"
    else -> "Auto ›"
}

fun PlayerUiState.captionsLabel(): String = when (captionsMode) {
    CaptionsMode.Lyrics -> "Sidecar ›"
    CaptionsMode.Off -> "Off ›"
}

fun nudgeSpeed(current: Float, delta: Float): Float {
    val stepped = round((current + delta) * 20f) / 20f
    return stepped.coerceIn(PlaybackSpeed.MIN, PlaybackSpeed.MAX)
}
