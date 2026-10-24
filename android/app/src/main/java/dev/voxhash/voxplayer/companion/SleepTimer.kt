package dev.voxhash.voxplayer.companion

import android.content.Context
import android.os.Bundle
import androidx.media3.session.SessionCommand

/**
 * Local sleep timer (no cloud). End time stored as epoch millis; ``0`` means off.
 * Fade runs in [PlaybackService] over the last ~30s before pause.
 */
object SleepTimer {
    const val PREFS = "voxplayer_sleep"
    const val KEY_END_EPOCH_MS = "end_epoch_ms"

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

    fun remainingLabel(endEpochMs: Long): String {
        if (endEpochMs <= 0L) return "Off"
        val left = ((endEpochMs - System.currentTimeMillis()) / 1000L).coerceAtLeast(0L)
        val m = left / 60
        val s = left % 60
        return "%d:%02d".format(m, s)
    }
}
