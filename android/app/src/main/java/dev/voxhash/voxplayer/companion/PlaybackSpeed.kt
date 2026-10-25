package dev.voxhash.voxplayer.companion

import android.content.Context
import android.os.Bundle
import androidx.media3.common.Player
import androidx.media3.session.SessionCommand
import kotlin.math.abs

/**
 * On-device playback rate for podcasts / spoken word (Media3
 * [Player.setPlaybackSpeed]). Pitch stays natural (default Media3 behavior).
 * No cloud / no proprietary audio SDK.
 * Optional sticky preferred rate (long-press) restores on cold start / reapply.
 */
object PlaybackSpeed {
    const val PREFS = "voxplayer_playback_speed"
    const val KEY_SPEED = "speed"
    const val KEY_PREFERRED = "preferred_speed"
    const val DEFAULT = 1.0f
    private const val NO_PREFERRED = -1f

    /** Common spoken-word / music rates. */
    val OPTIONS: List<Pair<Float, String>> = listOf(
        0.75f to "0.75×",
        1.0f to "1×",
        1.25f to "1.25×",
        1.5f to "1.5×",
        1.75f to "1.75×",
        2.0f to "2×",
    )

    const val ACTION_SET = "dev.voxhash.voxplayer.SET_PLAYBACK_SPEED"
    val CMD_SET: SessionCommand = SessionCommand(ACTION_SET, Bundle.EMPTY)
    const val EXTRA_SPEED = "speed"

    fun load(context: Context): Float =
        normalize(
            context.applicationContext
                .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .getFloat(KEY_SPEED, DEFAULT),
        )

    fun save(context: Context, speed: Float) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putFloat(KEY_SPEED, normalize(speed))
            .apply()
    }

    fun loadPreferred(context: Context): Float? {
        val raw = context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getFloat(KEY_PREFERRED, NO_PREFERRED)
        if (raw == NO_PREFERRED) return null
        return normalize(raw)
    }

    fun savePreferred(context: Context, speed: Float) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putFloat(KEY_PREFERRED, normalize(speed))
            .apply()
    }

    fun clearPreferred(context: Context) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_PREFERRED)
            .apply()
    }

    /** Preferred pin if set, else last selected speed. */
    fun loadBoot(context: Context): Float =
        loadPreferred(context) ?: load(context)

    fun normalize(speed: Float): Float {
        if (OPTIONS.any { abs(it.first - speed) < 0.001f }) {
            return OPTIONS.first { abs(it.first - speed) < 0.001f }.first
        }
        return OPTIONS.minBy { abs(it.first - speed) }.first
    }

    fun label(speed: Float): String =
        OPTIONS.firstOrNull { abs(it.first - normalize(speed)) < 0.001f }?.second ?: "1×"

    fun isSame(a: Float, b: Float): Boolean = abs(normalize(a) - normalize(b)) < 0.001f

    fun apply(player: Player, speed: Float) {
        val s = normalize(speed)
        try {
            player.setPlaybackSpeed(s)
        } catch (_: Exception) {
        }
    }
}
