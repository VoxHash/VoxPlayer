package dev.voxhash.voxplayer.companion

import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.PlaylistAdd
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.BookmarkBorder
import androidx.compose.material.icons.filled.Cast
import androidx.compose.material.icons.filled.Headphones
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.LockOpen
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material.icons.filled.SkipNext
import androidx.compose.material.icons.filled.SkipPrevious
import androidx.compose.material.icons.filled.Subtitles
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.Player

/**
 * Immersive full-screen Now Playing stage — dominant art/video, mode toggle, pill actions,
 * circular transport. FOSS / Media3 only; GrapheneOS-honest (no cloud account chrome).
 */
@Composable
fun NowPlayingStage(
    state: PlayerUiState,
    player: Player?,
    audioSurface: Boolean,
    onDismiss: () -> Unit,
    onAudioSurface: (Boolean) -> Unit,
    onPlayPause: () -> Unit,
    onPrev: () -> Unit,
    onNext: () -> Unit,
    onShuffle: () -> Unit,
    onSeek: (Long) -> Unit,
    onOpenCaptions: () -> Unit,
    onOpenSettings: () -> Unit,
    onShare: () -> Unit,
    onSaveList: () -> Unit,
    onCast: () -> Unit,
    onBookmark: () -> Unit,
    onOpenQueue: () -> Unit,
    onUnlock: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val title = state.localTitle.ifBlank { "Nothing playing" }
    val artUri = state.localQueue.firstOrNull { it.isCurrent }?.uri
        ?.takeIf { it.isNotBlank() }
        ?.let { Uri.parse(it) }
    val showVideo = !audioSurface && state.localIsVideo && player != null &&
        title != "(nothing loaded)"
    val showLyrics = state.captionsMode == CaptionsMode.Lyrics &&
        state.lyricsLines.isNotEmpty() &&
        (!state.localMuted || state.captionsShowWhenMuted)
    val ambient =
        state.ambientMode && state.qualityMode != "saver"

    if (state.screenLocked) {
        LockedNowPlayingStage(
            title = title,
            showVideo = showVideo,
            player = player,
            artUri = artUri,
            isVideo = state.localIsVideo,
            onUnlock = onUnlock,
            modifier = modifier,
        )
        return
    }

    Box(
        modifier
            .fillMaxSize()
            .background(
                if (ambient) {
                    Brush.radialGradient(
                        colors = listOf(Color(0xFF3D2418), VoxColors.BgApp, Color(0xFF0A0706)),
                    )
                } else {
                    Brush.verticalGradient(
                        listOf(
                            VoxColors.BgElevated,
                            VoxColors.BgApp,
                            Color(0xFF1A0F0C),
                        ),
                    )
                },
            ),
    ) {
        BoxWithConstraints(Modifier.fillMaxSize()) {
            val landscape = maxWidth > maxHeight * 1.05f
            if (landscape && showVideo) {
                LandscapeVideoStage(
                    state = state,
                    player = player,
                    title = title,
                    onDismiss = onDismiss,
                    onAudioSurface = onAudioSurface,
                    onPlayPause = onPlayPause,
                    onPrev = onPrev,
                    onNext = onNext,
                    onShuffle = onShuffle,
                    onSeek = onSeek,
                    onOpenCaptions = onOpenCaptions,
                    onOpenSettings = onOpenSettings,
                    onShare = onShare,
                    onSaveList = onSaveList,
                    onCast = onCast,
                    onBookmark = onBookmark,
                    onOpenQueue = onOpenQueue,
                )
            } else {
                PortraitStage(
                    state = state,
                    player = player,
                    title = title,
                    artUri = artUri,
                    showVideo = showVideo,
                    onDismiss = onDismiss,
                    onAudioSurface = onAudioSurface,
                    onPlayPause = onPlayPause,
                    onPrev = onPrev,
                    onNext = onNext,
                    onShuffle = onShuffle,
                    onSeek = onSeek,
                    onOpenCaptions = onOpenCaptions,
                    onOpenSettings = onOpenSettings,
                    onShare = onShare,
                    onSaveList = onSaveList,
                    onCast = onCast,
                    onBookmark = onBookmark,
                    onOpenQueue = onOpenQueue,
                )
            }
        }
        if (showLyrics) {
            LyricsOverlay(
                lines = state.lyricsLines,
                activeIndex = state.lyricsActiveIndex,
                modifier = Modifier
                    .align(Alignment.Center)
                    .fillMaxWidth()
                    .padding(horizontal = 28.dp),
            )
        }
    }
}

@Composable
private fun LockedNowPlayingStage(
    title: String,
    showVideo: Boolean,
    player: Player?,
    artUri: Uri?,
    isVideo: Boolean,
    onUnlock: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(modifier.fillMaxSize().background(Color.Black)) {
        StageSurface(showVideo, player, artUri, isVideo)
        Column(
            Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .background(Color(0xCC0A0706))
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Icon(Icons.Default.Lock, contentDescription = null, tint = VoxColors.TextSecondary)
            Spacer(Modifier.height(8.dp))
            Text(title, color = VoxColors.Text, maxLines = 2, textAlign = TextAlign.Center)
            Spacer(Modifier.height(12.dp))
            IconButton(onClick = onUnlock) {
                Icon(Icons.Default.LockOpen, contentDescription = "Unlock player controls", tint = VoxColors.Accent)
            }
            Text("Unlock controls", color = VoxColors.TextMuted, fontSize = 12.sp)
        }
    }
}

@Composable
private fun LyricsOverlay(
    lines: List<String>,
    activeIndex: Int,
    modifier: Modifier = Modifier,
) {
    val start = (activeIndex - 1).coerceAtLeast(0)
    val end = (activeIndex + 2).coerceAtMost(lines.lastIndex)
    if (start > end) return
    Column(
        modifier
            .clip(RoundedCornerShape(12.dp))
            .background(Color(0x990A0706))
            .padding(horizontal = 16.dp, vertical = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        for (i in start..end) {
            val active = i == activeIndex
            Text(
                lines[i],
                color = if (active) Color.White else VoxColors.TextMuted,
                fontWeight = if (active) FontWeight.SemiBold else FontWeight.Normal,
                fontSize = if (active) 18.sp else 14.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(vertical = 2.dp),
            )
        }
    }
}

@Composable
private fun PortraitStage(
    state: PlayerUiState,
    player: Player?,
    title: String,
    artUri: Uri?,
    showVideo: Boolean,
    onDismiss: () -> Unit,
    onAudioSurface: (Boolean) -> Unit,
    onPlayPause: () -> Unit,
    onPrev: () -> Unit,
    onNext: () -> Unit,
    onShuffle: () -> Unit,
    onSeek: (Long) -> Unit,
    onOpenCaptions: () -> Unit,
    onOpenSettings: () -> Unit,
    onShare: () -> Unit,
    onSaveList: () -> Unit,
    onCast: () -> Unit,
    onBookmark: () -> Unit,
    onOpenQueue: () -> Unit,
) {
    // Edge-to-edge surface: video/art fills the device window; chrome overlays top/bottom.
    // Avoids the Column+weight host that left postage-stamp frames on phone panels.
    Box(Modifier.fillMaxSize().background(Color.Black)) {
        Box(
            Modifier
                .fillMaxSize()
                .then(if (showVideo) Modifier else Modifier.padding(horizontal = 28.dp, vertical = 72.dp)),
            contentAlignment = Alignment.Center,
        ) {
            StageSurface(showVideo, player, artUri, state.localIsVideo)
        }
        Column(
            Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        0f to Color(0xCC0A0706),
                        0.18f to Color.Transparent,
                        0.55f to Color.Transparent,
                        1f to Color(0xF20A0706),
                    ),
                )
                .padding(horizontal = 20.dp, vertical = 12.dp),
        ) {
            StageTopBar(
                state = state,
                onDismiss = onDismiss,
                onAudioSurface = onAudioSurface,
                onBookmark = onBookmark,
                onCast = onCast,
                onOpenSettings = onOpenSettings,
            )
            Spacer(Modifier.weight(1f))
            StageMeta(title, state.localArtist)
            Spacer(Modifier.height(10.dp))
            StagePills(onOpenCaptions, onShare, onSaveList, onOpenQueue)
            Spacer(Modifier.height(8.dp))
            SeekScrubber(
                positionMs = state.localPositionMs,
                durationMs = state.localDurationMs,
                onSeek = onSeek,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(6.dp))
            StageTransport(state, onShuffle, onPrev, onPlayPause, onNext, onOpenSettings)
            Spacer(Modifier.height(8.dp))
            StageUpNext(state, onOpenQueue)
        }
    }
}

@Composable
private fun LandscapeVideoStage(
    state: PlayerUiState,
    player: Player?,
    title: String,
    onDismiss: () -> Unit,
    onAudioSurface: (Boolean) -> Unit,
    onPlayPause: () -> Unit,
    onPrev: () -> Unit,
    onNext: () -> Unit,
    onShuffle: () -> Unit,
    onSeek: (Long) -> Unit,
    onOpenCaptions: () -> Unit,
    onOpenSettings: () -> Unit,
    onShare: () -> Unit,
    onSaveList: () -> Unit,
    onCast: () -> Unit,
    onBookmark: () -> Unit,
    onOpenQueue: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxSize()
            .padding(12.dp),
        horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Box(
            Modifier
                .weight(1.55f)
                .fillMaxHeight()
                .clip(RoundedCornerShape(16.dp))
                .background(Color.Black),
            contentAlignment = Alignment.Center,
        ) {
            StageSurface(showVideo = true, player = player, artUri = null, isVideo = true)
        }
        Column(
            Modifier
                .weight(1f)
                .fillMaxHeight(),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            StageTopBar(
                state = state,
                onDismiss = onDismiss,
                onAudioSurface = onAudioSurface,
                onBookmark = onBookmark,
                onCast = onCast,
                onOpenSettings = onOpenSettings,
                compact = true,
            )
            StageMeta(title, state.localArtist)
            StagePills(onOpenCaptions, onShare, onSaveList, onOpenQueue)
            SeekScrubber(
                positionMs = state.localPositionMs,
                durationMs = state.localDurationMs,
                onSeek = onSeek,
                modifier = Modifier.fillMaxWidth(),
            )
            StageTransport(state, onShuffle, onPrev, onPlayPause, onNext, onOpenSettings)
            StageUpNext(state, onOpenQueue)
        }
    }
}

@Composable
private fun StageSurface(
    showVideo: Boolean,
    player: Player?,
    artUri: Uri?,
    isVideo: Boolean,
) {
    when {
        showVideo && player != null -> {
            AndroidView(
                factory = { ctx -> PlayerSurfaces.attachPlayerHost(ctx, player) },
                update = { host ->
                    host.bind(player)
                    host.requestLayout()
                },
                modifier = Modifier.fillMaxSize(),
            )
        }
        artUri != null -> {
            ArtworkThumb(
                contentUri = artUri,
                isVideo = isVideo,
                modifier = Modifier.fillMaxSize(),
                sizePx = 1024,
            )
        }
        else -> {
            Text(
                "VoxPlayer",
                color = VoxColors.Accent,
                fontWeight = FontWeight.Bold,
                fontSize = 28.sp,
            )
        }
    }
}

@Composable
private fun StageTopBar(
    state: PlayerUiState,
    onDismiss: () -> Unit,
    onAudioSurface: (Boolean) -> Unit,
    onBookmark: () -> Unit,
    onCast: () -> Unit,
    onOpenSettings: () -> Unit,
    compact: Boolean = false,
) {
    Row(
        Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = onDismiss) {
            Icon(
                Icons.Default.KeyboardArrowDown,
                contentDescription = "Close Now Playing",
                tint = VoxColors.Text,
            )
        }
        if (!compact) Spacer(Modifier.weight(1f))
        SurfaceModeToggle(
            audioSelected = state.stageAudioSurface || !state.localIsVideo,
            videoEnabled = state.localIsVideo,
            onAudio = { onAudioSurface(true) },
            onVideo = { onAudioSurface(false) },
        )
        if (!compact) Spacer(Modifier.weight(1f)) else Spacer(Modifier.weight(1f))
        IconButton(onClick = onBookmark) {
            val bookmarked = state.bookmarks.any { bm ->
                state.localQueue.firstOrNull { it.isCurrent }?.uri == bm.uri
            }
            Icon(
                if (bookmarked) Icons.Default.Bookmark else Icons.Default.BookmarkBorder,
                contentDescription = if (bookmarked) "Bookmarked" else "Favorite / bookmark",
                tint = if (bookmarked) VoxColors.Accent else VoxColors.TextSecondary,
            )
        }
        IconButton(onClick = onCast) {
            Icon(
                Icons.Default.Cast,
                contentDescription = "Cast to TV (DLNA)",
                tint = if (state.dlnaEnabled && state.dlnaSelectedId.isNotBlank()) {
                    VoxColors.Accent
                } else {
                    VoxColors.TextSecondary
                },
            )
        }
        IconButton(onClick = onOpenSettings) {
            Icon(Icons.Default.MoreVert, contentDescription = "More", tint = VoxColors.TextSecondary)
        }
    }
}

@Composable
private fun StageMeta(title: String, artist: String) {
    Text(
        title,
        style = MaterialTheme.typography.headlineSmall,
        color = VoxColors.Text,
        fontWeight = FontWeight.SemiBold,
        maxLines = 2,
        overflow = TextOverflow.Ellipsis,
    )
    if (artist.isNotBlank()) {
        Text(
            artist,
            style = MaterialTheme.typography.bodyLarge,
            color = VoxColors.TextSecondary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun StagePills(
    onOpenCaptions: () -> Unit,
    onShare: () -> Unit,
    onSaveList: () -> Unit,
    onOpenQueue: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        StagePill("Lyrics", Icons.Default.Subtitles, onOpenCaptions)
        StagePill("Share", Icons.Default.Share, onShare)
        StagePill("Save", Icons.AutoMirrored.Filled.PlaylistAdd, onSaveList)
        StagePill("Queue", Icons.Default.Shuffle, onOpenQueue)
    }
}

@Composable
private fun StageTransport(
    state: PlayerUiState,
    onShuffle: () -> Unit,
    onPrev: () -> Unit,
    onPlayPause: () -> Unit,
    onNext: () -> Unit,
    onOpenSettings: () -> Unit,
) {
    Row(
        Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceEvenly,
    ) {
        IconButton(onClick = onShuffle) {
            Icon(
                Icons.Default.Shuffle,
                contentDescription = "Shuffle",
                tint = if (state.localShuffle) VoxColors.Accent else VoxColors.TextSecondary,
            )
        }
        IconButton(onClick = onPrev) {
            Icon(
                Icons.Default.SkipPrevious,
                contentDescription = "Previous",
                tint = VoxColors.Text,
                modifier = Modifier.size(36.dp),
            )
        }
        Box(
            Modifier
                .size(72.dp)
                .clip(CircleShape)
                .background(VoxColors.Text)
                .clickable(onClick = onPlayPause),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                if (state.localPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                contentDescription = if (state.localPlaying) "Pause" else "Play",
                tint = VoxColors.BgApp,
                modifier = Modifier.size(40.dp),
            )
        }
        IconButton(onClick = onNext) {
            Icon(
                Icons.Default.SkipNext,
                contentDescription = "Next",
                tint = VoxColors.Text,
                modifier = Modifier.size(36.dp),
            )
        }
        IconButton(onClick = onOpenSettings) {
            Icon(Icons.Default.MoreVert, contentDescription = "Player settings", tint = VoxColors.TextSecondary)
        }
    }
}

@Composable
private fun StageUpNext(state: PlayerUiState, onOpenQueue: () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp))
            .background(VoxColors.BgElevated.copy(alpha = 0.85f))
            .clickable(onClick = onOpenQueue)
            .padding(vertical = 10.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            Modifier
                .width(36.dp)
                .height(4.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(VoxColors.BorderSoft),
        )
        Spacer(Modifier.height(6.dp))
        Text(
            if (state.localQueueSize > 0) {
                "Up next · ${state.localQueueIndex + 1}/${state.localQueueSize}"
            } else {
                "Up next"
            },
            color = VoxColors.TextMuted,
            style = MaterialTheme.typography.labelLarge,
        )
    }
}

@Composable
private fun SurfaceModeToggle(
    audioSelected: Boolean,
    videoEnabled: Boolean,
    onAudio: () -> Unit,
    onVideo: () -> Unit,
) {
    Row(
        Modifier
            .clip(RoundedCornerShape(24.dp))
            .background(VoxColors.BgHover)
            .padding(3.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        ModeChip(Icons.Default.Headphones, audioSelected, onAudio)
        ModeChip(
            Icons.Default.Videocam,
            !audioSelected && videoEnabled,
            onClick = { if (videoEnabled) onVideo() },
            enabled = videoEnabled,
        )
    }
}

@Composable
private fun ModeChip(
    icon: ImageVector,
    selected: Boolean,
    onClick: () -> Unit,
    enabled: Boolean = true,
) {
    Box(
        Modifier
            .size(40.dp)
            .clip(CircleShape)
            .background(if (selected) VoxColors.Text else Color.Transparent)
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            icon,
            contentDescription = null,
            tint = when {
                !enabled -> VoxColors.TextMuted
                selected -> VoxColors.BgApp
                else -> VoxColors.TextSecondary
            },
        )
    }
}

@Composable
private fun StagePill(label: String, icon: ImageVector, onClick: () -> Unit) {
    Row(
        Modifier
            .clip(RoundedCornerShape(20.dp))
            .background(VoxColors.BgHover.copy(alpha = 0.9f))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Icon(icon, contentDescription = label, tint = VoxColors.Text, modifier = Modifier.size(18.dp))
        Text(label, color = VoxColors.Text, fontSize = 13.sp, fontWeight = FontWeight.Medium)
    }
}
