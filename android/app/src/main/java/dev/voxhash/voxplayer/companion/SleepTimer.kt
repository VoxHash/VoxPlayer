package dev.voxhash.voxplayer.companion

import android.content.Context
import android.os.Bundle
import androidx.media3.session.SessionCommand

/**
 * Local sleep timer (no cloud). End time stored as epoch millis; ``0`` means off.
 * Fade runs in [PlaybackService] over the last ~30s before pause.
 * Optional sticky preferred duration (long-press) for one-tap re-arm.
 */
object SleepTimer {
    const val PREFS = "voxplayer_sleep"
    const val KEY_END_EPOCH_MS = "end_epoch_ms"
    const val KEY_PREFERRED_MIN = "preferred_minutes"
    private const val NO_PREFERRED = -1

    val DURATIONS_MIN: List<Int> = listOf(15, 30, 45, 60, 90)

    const val ACTION_SET = "dev.voxhash.voxplayer.SET_SLEEP_TIMER"
    val CMD_SET: SessionCommand = SessionCommand(ACTION_SET, Bundle.EMPTY)
    const val EXTRA_MINUTES = "minutes" // 0 = clear
    const val EXTRA_END_EPOCH_MS = "end_epoch_ms"

    const val ACTION_FIRED = "dev.voxhash.voxplayer.SLEEP_TIMER_FIRED"

    fun loadEndEpochMs(context: Context): Long =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getLong(KEY_END_EPOCH_MS, 0L)
            .let { if (it > System.currentTimeMillis()) it else 0L }

    fun saveEndEpochMs(context: Context, endEpochMs: Long) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putLong(KEY_END_EPOCH_MS, endEpochMs.coerceAtLeast(0L))
            .apply()
    }

    fun loadPreferredMinutes(context: Context): Int? {
        val raw = context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getInt(KEY_PREFERRED_MIN, NO_PREFERRED)
        if (raw == NO_PREFERRED) return null
        return normalizeMinutes(raw)
    }

    fun savePreferredMinutes(context: Context, minutes: Int) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_PREFERRED_MIN, normalizeMinutes(minutes))
            .apply()
    }

    fun clearPreferredMinutes(context: Context) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_PREFERRED_MIN)
            .apply()
    }

    fun normalizeMinutes(minutes: Int): Int {
        if (minutes in DURATIONS_MIN) return minutes
        return DURATIONS_MIN.minBy { kotlin.math.abs(it - minutes) }
    }

    fun remainingLabel(endEpochMs: Long): String {
        if (endEpochMs <= 0L) return "Off"
        val left = ((endEpochMs - System.currentTimeMillis()) / 1000L).coerceAtLeast(0L)
        val m = left / 60
        val s = left % 60
        return "%d:%02d".format(m, s)
    }
}
