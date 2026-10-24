package dev.voxhash.voxplayer.companion

import android.content.Context
import android.media.audiofx.LoudnessEnhancer
import android.os.Bundle
import android.util.Log
import androidx.media3.common.C
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.SessionCommand
import kotlin.math.ln
import kotlin.math.roundToInt

/**
 * Desktop-parity local volume: logical **0–200%** + mute.
 *
 * - 0–100%: ExoPlayer `volume` 0f–1f
 * - 101–200%: player at 1f + AOSP [LoudnessEnhancer] gain so 200% ≈ +6 dB (2× amplitude)
 *
 * No GMS / proprietary boost SDKs. GrapheneOS: effect may be unavailable on some
 * builds — we still apply the 0–100% path and log when enhancer attach fails.
 */
object LocalVolume {
    const val PREFS = "voxplayer_local_volume"
    const val KEY_PERCENT = "percent"
    const val KEY_MUTED = "muted"
    const val DEFAULT_PERCENT = 100

    const val ACTION_SET = "dev.voxhash.voxplayer.SET_LOCAL_VOLUME"
    val CMD_SET: SessionCommand = SessionCommand(ACTION_SET, Bundle.EMPTY)

    const val EXTRA_PERCENT = "percent"
    const val EXTRA_MUTED = "muted"

    fun loadPercent(context: Context): Int =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getInt(KEY_PERCENT, DEFAULT_PERCENT)
            .coerceIn(0, 200)

    fun loadMuted(context: Context): Boolean =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean(KEY_MUTED, false)

    fun save(context: Context, percent: Int, muted: Boolean) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_PERCENT, percent.coerceIn(0, 200))
            .putBoolean(KEY_MUTED, muted)
            .apply()
    }

    /** Target gain in millibels for percent in (100, 200]. 200% → ~+602 mB (+6 dB). */
    fun boostGainMb(percent: Int): Int {
        if (percent <= 100) return 0
        val ratio = percent.coerceAtMost(200) / 100.0
        // 20 * log10(ratio) * 100 mB; log10(x) = ln(x)/ln(10)
        return (2000.0 * ln(ratio) / ln(10.0)).roundToInt().coerceAtLeast(0)
    }

    fun playerVolume(percent: Int, muted: Boolean): Float {
        if (muted || percent <= 0) return 0f
        return (percent.coerceAtMost(100) / 100f).coerceIn(0f, 1f)
    }
}

/**
 * Applies [LocalVolume] settings to an [ExoPlayer], attaching [LoudnessEnhancer]
 * when the audio session is ready.
 */
class LocalVolumeApplier {
    private var enhancer: LoudnessEnhancer? = null
    private var enhancerSessionId: Int = C.AUDIO_SESSION_ID_UNSET

    fun apply(player: Player, percent: Int, muted: Boolean) {
        val pct = percent.coerceIn(0, 200)
        player.volume = LocalVolume.playerVolume(pct, muted)
        if (player !is ExoPlayer) return
        val sessionId = player.audioSessionId
        if (sessionId == 0 || sessionId == C.AUDIO_SESSION_ID_UNSET) {
            return
        }
        if (sessionId != enhancerSessionId) {
            releaseEnhancer()
            enhancer = try {
                LoudnessEnhancer(sessionId).also { it.enabled = true }
            } catch (e: Exception) {
                Log.w(TAG, "LoudnessEnhancer unavailable (session=$sessionId)", e)
                null
            }
            enhancerSessionId = sessionId
        }
        val boost = if (muted || pct <= 100) 0 else LocalVolume.boostGainMb(pct)
        try {
            enhancer?.setTargetGain(boost)
            enhancer?.enabled = !muted && pct > 100 && boost > 0
        } catch (e: Exception) {
            Log.w(TAG, "LoudnessEnhancer setTargetGain failed", e)
        }
    }

    fun release() {
        releaseEnhancer()
    }

    private fun releaseEnhancer() {
        try {
            enhancer?.enabled = false
            enhancer?.release()
        } catch (_: Exception) {
        }
        enhancer = null
        enhancerSessionId = C.AUDIO_SESSION_ID_UNSET
    }

    companion object {
        private const val TAG = "VoxLocalVolume"
    }
}
