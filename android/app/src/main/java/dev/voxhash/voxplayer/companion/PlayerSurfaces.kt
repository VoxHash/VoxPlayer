package dev.voxhash.voxplayer.companion

import android.content.Context
import android.os.Build
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import androidx.media3.common.Player
import androidx.media3.exoplayer.DefaultLoadControl
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.AspectRatioFrameLayout
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

    fun attachPlayerView(context: Context, player: Player?): PlayerView {
        val view = android.view.LayoutInflater.from(context)
            .inflate(dev.voxhash.voxplayer.companion.R.layout.player_view_fill, null, false)
            as PlayerView
        return view.apply {
            this.player = player
            useController = false
            setKeepContentOnPlayerReset(true)
            setShowBuffering(PlayerView.SHOW_BUFFERING_NEVER)
            // ZOOM fills the Compose host (crop edges). TextureView (XML surface_type)
            // avoids SurfaceView postage-stamp compositing inside AndroidView.
            resizeMode = AspectRatioFrameLayout.RESIZE_MODE_ZOOM
            setArtworkDisplayMode(PlayerView.ARTWORK_DISPLAY_MODE_OFF)
            setShutterBackgroundColor(android.graphics.Color.BLACK)
            layoutParams = FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
                Gravity.CENTER,
            )
        }
    }

    /**
     * Compose [androidx.compose.ui.viewinterop.AndroidView] host that forces EXACTLY
     * width/height on the [PlayerView]. Without this, AspectRatioFrameLayout measures
     * to the video aspect (AT_MOST) and leaves a postage-stamp frame in the stage.
     */
    fun attachPlayerHost(context: Context, player: Player?): PlayerHost =
        PlayerHost(context, player)
}

/** Forces EXACTLY measure specs onto Media3 [PlayerView] for Compose interop. */
class PlayerHost(context: Context, player: Player?) : FrameLayout(context) {
    private val playerView = PlayerSurfaces.attachPlayerView(context, player)

    init {
        addView(
            playerView,
            LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
                Gravity.CENTER,
            ),
        )
    }

    fun bind(p: Player?) {
        playerView.player = p
        playerView.resizeMode = AspectRatioFrameLayout.RESIZE_MODE_ZOOM
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val w = View.MeasureSpec.getSize(widthMeasureSpec).coerceAtLeast(1)
        val h = View.MeasureSpec.getSize(heightMeasureSpec).coerceAtLeast(1)
        setMeasuredDimension(w, h)
        val childSpecW = View.MeasureSpec.makeMeasureSpec(w, View.MeasureSpec.EXACTLY)
        val childSpecH = View.MeasureSpec.makeMeasureSpec(h, View.MeasureSpec.EXACTLY)
        for (i in 0 until childCount) {
            getChildAt(i).measure(childSpecW, childSpecH)
        }
    }

    override fun onLayout(changed: Boolean, left: Int, top: Int, right: Int, bottom: Int) {
        for (i in 0 until childCount) {
            getChildAt(i).layout(0, 0, right - left, bottom - top)
        }
    }
}

fun ExoPlayer.Builder.applyVoxLoadControl(context: Context): ExoPlayer.Builder =
    setLoadControl(PlayerSurfaces.loadControl(context))
