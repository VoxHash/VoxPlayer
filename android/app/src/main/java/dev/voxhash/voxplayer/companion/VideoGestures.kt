package dev.voxhash.voxplayer.companion

import android.app.Activity
import android.content.Context
import android.view.WindowManager
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.unit.dp
import kotlin.math.abs
import kotlin.math.roundToInt

private enum class VideoGestureKind { None, Seek, Volume, Brightness }

/**
 * Overlay gestures on the local video surface (Media3):
 * - Horizontal drag → scrub / seek
 * - Left third vertical → window brightness
 * - Right third vertical → app volume 0–200%
 *
 * No GMS. GrapheneOS: brightness is window-local; volume uses Media3 + AOSP LoudnessEnhancer path.
 */
@Composable
fun VideoGestureSurface(
    positionMs: Long,
    durationMs: Long,
    volumePercent: Int,
    onSeek: (Long) -> Unit,
    onVolumePercent: (Int) -> Unit,
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit,
) {
    val context = LocalContext.current
    val density = LocalDensity.current
    val haptics = LocalHapticFeedback.current
    val positionState = rememberUpdatedState(positionMs)
    val durationState = rememberUpdatedState(durationMs)
    val volumeState = rememberUpdatedState(volumePercent)
    val onSeekState = rememberUpdatedState(onSeek)
    val onVolumeState = rememberUpdatedState(onVolumePercent)

    var hud by remember { mutableStateOf<String?>(null) }
    var kind by remember { mutableStateOf(VideoGestureKind.None) }
    var startPosMs by remember { mutableLongStateOf(0L) }
    var startVolume by remember { mutableFloatStateOf(100f) }
    var startBrightness by remember { mutableFloatStateOf(0.5f) }
    var accumX by remember { mutableFloatStateOf(0f) }
    var accumY by remember { mutableFloatStateOf(0f) }
    var startInLeft by remember { mutableStateOf(true) }

    Box(modifier) {
        content()
        Box(
            Modifier
                .fillMaxSize()
                .pointerInput(Unit) {
                    val slop = with(density) { 16.dp.toPx() }
                    detectDragGestures(
                        onDragStart = { offset: Offset ->
                            kind = VideoGestureKind.None
                            accumX = 0f
                            accumY = 0f
                            startPosMs = positionState.value.coerceAtLeast(0L)
                            startVolume = volumeState.value.toFloat()
                            startInLeft = offset.x < size.width * 0.4f
                            startBrightness = readWindowBrightness(context)
                            hud = null
                        },
                        onDrag = { change, dragAmount ->
                            change.consume()
                            accumX += dragAmount.x
                            accumY += dragAmount.y
                            if (kind == VideoGestureKind.None) {
                                if (abs(accumX) < slop && abs(accumY) < slop) return@detectDragGestures
                                kind = when {
                                    abs(accumX) >= abs(accumY) -> VideoGestureKind.Seek
                                    startInLeft -> VideoGestureKind.Brightness
                                    else -> VideoGestureKind.Volume
                                }
                                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                            }
                            when (kind) {
                                VideoGestureKind.Seek -> {
                                    val dur = durationState.value.coerceAtLeast(0L)
                                    if (dur <= 0L) {
                                        hud = "Seek…"
                                        return@detectDragGestures
                                    }
                                    // Full width ≈ ±60s or 25% of duration, whichever larger.
                                    val spanMs = maxOf(60_000L, (dur * 0.25f).toLong())
                                    val delta = (accumX / size.width.toFloat()) * spanMs
                                    val target = (startPosMs + delta.toLong()).coerceIn(0L, dur)
                                    // Preview only while dragging — seek on release.
                                    // Per-frame seekTo floods Quest HAS deep-buffer / spatialize
                                    // and can leave a continuous hiss after scrubbing.
                                    hud = "Seek  ${fmtGestureMs(target)} / ${fmtGestureMs(dur)}"
                                }
                                VideoGestureKind.Volume -> {
                                    // Full height ≈ ±100 volume points.
                                    val delta = (-accumY / size.height.toFloat()) * 100f
                                    val next = (startVolume + delta).roundToInt().coerceIn(0, 200)
                                    hud = "Volume  $next%"
                                    onVolumeState.value(next)
                                }
                                VideoGestureKind.Brightness -> {
                                    val delta = -accumY / size.height.toFloat()
                                    val next = (startBrightness + delta).coerceIn(0.05f, 1f)
                                    writeWindowBrightness(context, next)
                                    hud = "Brightness  ${(next * 100f).roundToInt()}%"
                                }
                                VideoGestureKind.None -> Unit
                            }
                        },
                        onDragEnd = {
                            if (kind == VideoGestureKind.Seek) {
                                val dur = durationState.value.coerceAtLeast(0L)
                                if (dur > 0L) {
                                    val spanMs = maxOf(60_000L, (dur * 0.25f).toLong())
                                    val delta = (accumX / size.width.toFloat()) * spanMs
                                    val target = (startPosMs + delta.toLong()).coerceIn(0L, dur)
                                    onSeekState.value(target)
                                }
                            }
                            kind = VideoGestureKind.None
                            hud = null
                        },
                        onDragCancel = {
                            kind = VideoGestureKind.None
                            hud = null
                        },
                    )
                },
        )
        hud?.let { label ->
            Text(
                label,
                color = Color.White,
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier
                    .align(Alignment.Center)
                    .background(Color.Black.copy(alpha = 0.62f), RoundedCornerShape(10.dp))
                    .padding(horizontal = 16.dp, vertical = 10.dp),
            )
        }
    }
}

private fun fmtGestureMs(ms: Long): String {
    val sec = (ms / 1000).coerceAtLeast(0)
    return "%d:%02d".format(sec / 60, sec % 60)
}

private fun readWindowBrightness(context: Context): Float {
    val activity = context.findActivity() ?: return 0.5f
    val raw = activity.window.attributes.screenBrightness
    return if (raw < 0f) 0.5f else raw.coerceIn(0.05f, 1f)
}

private fun writeWindowBrightness(context: Context, value: Float) {
    val activity = context.findActivity() ?: return
    val lp = activity.window.attributes
    lp.screenBrightness = value.coerceIn(0.05f, 1f)
    activity.window.attributes = lp
    // Ensure we are not stuck on BRIGHTNESS_OVERRIDE_NONE after first gesture.
    if (lp.screenBrightness < 0f) {
        lp.screenBrightness = value.coerceIn(0.05f, 1f)
        activity.window.attributes = lp
    }
    // Keep FLAG so override sticks for this Activity (panel / Quest).
    activity.window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
}
