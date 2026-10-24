package dev.voxhash.voxplayer.companion

import android.content.Context
import android.media.audiofx.Equalizer
import android.os.Bundle
import android.util.Log
import androidx.media3.common.C
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.SessionCommand

/**
 * AOSP [Equalizer] presets for on-device playback (no proprietary EQ SDK).
 * GrapheneOS / some builds may omit the effect — Off still works.
 */
object EqualizerControl {
    const val PREFS = "voxplayer_eq"
    const val KEY_PRESET = "preset"
    const val PRESET_OFF = "off"
    const val PRESET_FLAT = "flat"
    const val PRESET_BASS = "bass"
    const val PRESET_TREBLE = "treble"
    const val PRESET_VOCAL = "vocal"
    const val PRESET_LOUDNESS = "loudness"

    val PRESETS: List<Pair<String, String>> = listOf(
        PRESET_OFF to "Off",
        PRESET_FLAT to "Flat",
        PRESET_BASS to "Bass",
        PRESET_TREBLE to "Treble",
        PRESET_VOCAL to "Vocal",
        PRESET_LOUDNESS to "Loud",
    )

    const val ACTION_SET = "dev.voxhash.voxplayer.SET_EQ_PRESET"
    val CMD_SET: SessionCommand = SessionCommand(ACTION_SET, Bundle.EMPTY)
    const val EXTRA_PRESET = "preset"

    fun loadPreset(context: Context): String =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_PRESET, PRESET_OFF)
            ?.takeIf { id -> PRESETS.any { it.first == id } }
            ?: PRESET_OFF

    fun savePreset(context: Context, preset: String) {
        val id = preset.takeIf { p -> PRESETS.any { it.first == p } } ?: PRESET_OFF
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_PRESET, id)
            .apply()
    }
}

class EqualizerApplier {
    private var equalizer: Equalizer? = null
    private var sessionId: Int = C.AUDIO_SESSION_ID_UNSET
    private var preset: String = EqualizerControl.PRESET_OFF

    fun setPreset(name: String) {
        preset = name.takeIf { p -> EqualizerControl.PRESETS.any { it.first == p } }
            ?: EqualizerControl.PRESET_OFF
        applyBands()
    }

    fun apply(player: Player) {
        if (player !is ExoPlayer) return
        val id = player.audioSessionId
        if (id == 0 || id == C.AUDIO_SESSION_ID_UNSET) return
        if (id != sessionId) {
            releaseEq()
            equalizer = try {
                Equalizer(0, id).also { it.enabled = preset != EqualizerControl.PRESET_OFF }
            } catch (e: Exception) {
                Log.w(TAG, "Equalizer unavailable (session=$id)", e)
                null
            }
            sessionId = id
        }
        applyBands()
    }

    fun release() = releaseEq()

    private fun applyBands() {
        val eq = equalizer ?: return
        try {
            if (preset == EqualizerControl.PRESET_OFF) {
                eq.enabled = false
                return
            }
            eq.enabled = true
            val bands = eq.numberOfBands.toInt()
            if (bands <= 0) return
            val min = eq.bandLevelRange[0]
            val max = eq.bandLevelRange[1]
            val mid = 0.toShort()
            fun level(frac: Float): Short {
                val span = if (frac >= 0f) max.toInt() else -min.toInt()
                return (frac * span).toInt().coerceIn(min.toInt(), max.toInt()).toShort()
            }
            // Shape bands low → high by preset (millibels-ish short levels)
            val shape: (Int) -> Float = when (preset) {
                EqualizerControl.PRESET_BASS -> { i ->
                    val t = i / (bands - 1f).coerceAtLeast(1f)
                    (1f - t) * 0.85f - t * 0.15f
                }
                EqualizerControl.PRESET_TREBLE -> { i ->
                    val t = i / (bands - 1f).coerceAtLeast(1f)
                    t * 0.85f - (1f - t) * 0.1f
                }
                EqualizerControl.PRESET_VOCAL -> { i ->
                    val t = i / (bands - 1f).coerceAtLeast(1f)
                    // mid bump
                    1f - kotlin.math.abs(t - 0.45f) * 2.2f
                }
                EqualizerControl.PRESET_LOUDNESS -> { i ->
                    val t = i / (bands - 1f).coerceAtLeast(1f)
                    // mild smile curve
                    0.55f * (1f - 4f * (t - 0.5f) * (t - 0.5f)) + 0.25f
                }
                else -> { _ -> 0f } // flat
            }
            for (i in 0 until bands) {
                val band = i.toShort()
                val lvl = if (preset == EqualizerControl.PRESET_FLAT) mid else level(shape(i).coerceIn(-1f, 1f))
                eq.setBandLevel(band, lvl)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Equalizer apply failed", e)
        }
    }

    private fun releaseEq() {
        try {
            equalizer?.enabled = false
            equalizer?.release()
        } catch (_: Exception) {
        }
        equalizer = null
        sessionId = C.AUDIO_SESSION_ID_UNSET
    }

    companion object {
        private const val TAG = "VoxEqualizer"
    }
}
