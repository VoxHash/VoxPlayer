package dev.voxhash.voxplayer.companion

import android.content.Context
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.media3.common.Player
import androidx.media3.session.SessionCommand
import kotlin.math.abs

/**
 * Soft fade-in on auto track transitions and optional silence skip.
 * True dual-stream crossfade needs two players; this covers mixed-codec
 * gap clicks by ramping ExoPlayer volume after MEDIA_ITEM_TRANSITION.
 * Fade duration is user-selectable (Short / Med / Long / Soft).
 */
object CrossfadeControl {
    const val PREFS = "voxplayer_crossfade"
    const val KEY_CROSSFADE = "crossfade_enabled"
    const val KEY_SKIP_SILENCE = "skip_silence"
    const val KEY_FADE_MS = "fade_ms"
    /** Sticky preferred fade length (long-press). */
    const val KEY_PREFERRED_FADE_MS = "preferred_fade_ms"
    const val FADE_STEPS = 12
    const val DEFAULT_FADE_MS = 450L
    private const val NO_PREFERRED = -1L

    /** Selectable fade-in lengths (ms) with UI labels. */
    val FADE_OPTIONS: List<Pair<Long, String>> = listOf(
        250L to "Short",
        450L to "Med",
        800L to "Long",
        1200L to "Soft",
    )

    const val ACTION_SET = "dev.voxhash.voxplayer.SET_CROSSFADE"
    val CMD_SET: SessionCommand = SessionCommand(ACTION_SET, Bundle.EMPTY)

    const val EXTRA_CROSSFADE = "crossfade"
    const val EXTRA_SKIP_SILENCE = "skip_silence"
    const val EXTRA_FADE_MS = "fade_ms"

    fun loadCrossfade(context: Context): Boolean =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean(KEY_CROSSFADE, true)

    fun loadSkipSilence(context: Context): Boolean =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean(KEY_SKIP_SILENCE, false)

    fun loadFadeMs(context: Context): Long =
        normalizeFadeMs(
            context.applicationContext
                .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .getLong(KEY_FADE_MS, DEFAULT_FADE_MS),
        )

    fun loadPreferredFadeMs(context: Context): Long? {
        val raw = context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getLong(KEY_PREFERRED_FADE_MS, NO_PREFERRED)
        if (raw == NO_PREFERRED) return null
        return normalizeFadeMs(raw)
    }

    fun savePreferredFadeMs(context: Context, fadeMs: Long) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putLong(KEY_PREFERRED_FADE_MS, normalizeFadeMs(fadeMs))
            .apply()
    }

    fun clearPreferredFadeMs(context: Context) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_PREFERRED_FADE_MS)
            .apply()
    }

    /** Preferred pin if set, else last selected fade. */
    fun loadBootFadeMs(context: Context): Long =
        loadPreferredFadeMs(context) ?: loadFadeMs(context)

    fun normalizeFadeMs(ms: Long): Long {
        if (FADE_OPTIONS.any { it.first == ms }) return ms
        return FADE_OPTIONS.minBy { abs(it.first - ms) }.first
    }

    fun fadeLabel(ms: Long): String =
        FADE_OPTIONS.firstOrNull { it.first == normalizeFadeMs(ms) }?.second ?: "Med"

    fun save(
        context: Context,
        crossfade: Boolean,
        skipSilence: Boolean,
        fadeMs: Long = loadFadeMs(context),
    ) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_CROSSFADE, crossfade)
            .putBoolean(KEY_SKIP_SILENCE, skipSilence)
            .putLong(KEY_FADE_MS, normalizeFadeMs(fadeMs))
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
        fadeMs: Long = CrossfadeControl.DEFAULT_FADE_MS,
    ) {
        cancel()
        if (!enabled || muted || targetVolume <= 0f) {
            player.volume = if (muted) 0f else targetVolume
            return
        }
        val duration = CrossfadeControl.normalizeFadeMs(fadeMs).coerceAtLeast(50L)
        player.volume = 0f
        val steps = CrossfadeControl.FADE_STEPS
        val stepMs = (duration / steps).coerceAtLeast(1L)
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
