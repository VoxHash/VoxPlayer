package dev.voxhash.voxplayer.companion

import android.content.Context
import android.os.Build
import androidx.media3.common.Player
import androidx.media3.exoplayer.DefaultLoadControl
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView

/**
 * Shared Media3 surface + buffer helpers tuned for phone / GrapheneOS / Quest panels.
 * TextureView keeps Compose interop cheap; tighter buffers cut RAM on VR SoCs.
 */
object PlayerSurfaces {
    /** Heuristic: Meta Quest / Horizon panel or low-RAM devices prefer leaner buffers. */
    fun leanDevice(context: Context): Boolean {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as? android.app.ActivityManager
        val lowRam = am?.isLowRamDevice == true
        val model = Build.MODEL.orEmpty().lowercase()
        val product = Build.PRODUCT.orEmpty().lowercase()
        val horizon = product.contains("eureka") || model.contains("quest")
        return lowRam || horizon
    }

    fun loadControl(context: Context): DefaultLoadControl {
        val lean = leanDevice(context)
        val builder = DefaultLoadControl.Builder()
        return if (lean) {
            builder
                .setBufferDurationsMs(
                    /* minBufferMs = */ 8_000,
                    /* maxBufferMs = */ 28_000,
                    /* bufferForPlaybackMs = */ 750,
                    /* bufferForPlaybackAfterRebufferMs = */ 2_000,
                )
                .setPrioritizeTimeOverSizeThresholds(true)
                .build()
        } else {
            builder
                .setBufferDurationsMs(
                    /* minBufferMs = */ 15_000,
                    /* maxBufferMs = */ 50_000,
                    /* bufferForPlaybackMs = */ 1_250,
                    /* bufferForPlaybackAfterRebufferMs = */ 2_500,
                )
                .build()
        }
    }

    fun attachPlayerView(context: Context, player: Player?): PlayerView =
        PlayerView(context).apply {
            this.player = player
            useController = false
            setKeepContentOnPlayerReset(true)
            setShowBuffering(PlayerView.SHOW_BUFFERING_NEVER)
            // Prefer texture_view via layout inflater attrs when an XML host is used;
            // programmatic PlayerView defaults remain valid for Compose AndroidView.
        }
}

fun ExoPlayer.Builder.applyVoxLoadControl(context: Context): ExoPlayer.Builder =
    setLoadControl(PlayerSurfaces.loadControl(context))
