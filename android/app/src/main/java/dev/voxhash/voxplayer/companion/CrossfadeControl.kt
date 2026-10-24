package dev.voxhash.voxplayer.companion

import android.content.Context
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.media3.common.Player
import androidx.media3.session.SessionCommand

/**
 * Soft fade-in on auto track transitions and optional silence skip.
 * True dual-stream crossfade needs two players; this covers mixed-codec
 * gap clicks by ramping ExoPlayer volume after MEDIA_ITEM_TRANSITION.
 */
object CrossfadeControl {
    const val PREFS = "voxplayer_crossfade"
    const val KEY_CROSSFADE = "crossfade_enabled"
    const val KEY_SKIP_SILENCE = "skip_silence"
    const val FADE_MS = 450L
    const val FADE_STEPS = 12

    const val ACTION_SET = "dev.voxhash.voxplayer.SET_CROSSFADE"
    val CMD_SET: SessionCommand = SessionCommand(ACTION_SET, Bundle.EMPTY)

    const val EXTRA_CROSSFADE = "crossfade"
    const val EXTRA_SKIP_SILENCE = "skip_silence"

    fun loadCrossfade(context: Context): Boolean =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean(KEY_CROSSFADE, true)

    fun loadSkipSilence(context: Context): Boolean =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean(KEY_SKIP_SILENCE, false)

    fun save(context: Context, crossfade: Boolean, skipSilence: Boolean) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_CROSSFADE, crossfade)
            .putBoolean(KEY_SKIP_SILENCE, skipSilence)
            .apply()
    }
}

class CrossfadeApplier {
    private val handler = Handler(Looper.getMainLooper())
    private var fadeRunnable: Runnable? = null

    fun isActive(): Boolean = fadeRunnable != null

    fun cancel() {
        fadeRunnable?.let { handler.removeCallbacks(it) }
        fadeRunnable = null
    }

    fun onAutoTransition(
        player: Player,
        enabled: Boolean,
        targetVolume: Float,
        muted: Boolean,
    ) {
        cancel()
        if (!enabled || muted || targetVolume <= 0f) {
            player.volume = if (muted) 0f else targetVolume
            return
        }
        player.volume = 0f
        val steps = CrossfadeControl.FADE_STEPS
        val stepMs = CrossfadeControl.FADE_MS / steps
        var i = 0
        val run = object : Runnable {
            override fun run() {
                i++
                val frac = (i.toFloat() / steps).coerceIn(0f, 1f)
                player.volume = targetVolume * frac
                if (i < steps) {
                    handler.postDelayed(this, stepMs)
                } else {
                    fadeRunnable = null
                }
            }
        }
        fadeRunnable = run
        handler.postDelayed(run, stepMs)
    }

    fun release() = cancel()
}
