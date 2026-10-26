package dev.voxhash.voxplayer.companion

import android.content.Context
import android.media.audiofx.Equalizer
import android.os.Bundle
import android.util.Log
import androidx.media3.common.C
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.SessionCommand
import org.json.JSONArray
import kotlin.math.abs
import kotlin.math.ln
import kotlin.math.roundToInt

/**
 * AOSP [Equalizer] presets + custom 10-band sheet (preamp / snap). No proprietary EQ SDK.
 * GrapheneOS / some builds may omit the effect — Off still works.
 */
object EqualizerControl {
    const val PREFS = "voxplayer_eq"
    const val KEY_PRESET = "preset"
    /** Sticky preferred preset (long-press); applied on cold start / audio reapply. */
    const val KEY_PREFERRED = "preferred_preset"
    const val KEY_BANDS = "bands_db_json"
    const val KEY_PREAMP = "preamp_db"
    const val KEY_SNAP = "snap_bands"
    const val PRESET_OFF = "off"
    const val PRESET_FLAT = "flat"
    const val PRESET_BASS = "bass"
    const val PRESET_TREBLE = "treble"
    const val PRESET_VOCAL = "vocal"
    const val PRESET_LOUDNESS = "loudness"
    const val PRESET_CUSTOM = "custom"

    const val BAND_COUNT = 10
    /** UI center frequencies (Hz) — mapped onto whatever AOSP reports. */
    val BAND_HZ: FloatArray = floatArrayOf(
        31f, 63f, 125f, 250f, 500f, 1_000f, 2_000f, 4_000f, 8_000f, 16_000f,
    )
    val BAND_LABELS: List<String> = listOf(
        "31Hz", "63Hz", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz", "16kHz",
    )
    const val GAIN_MIN_DB = -12f
    const val GAIN_MAX_DB = 12f
    const val PREAMP_MIN_DB = -12f
    const val PREAMP_MAX_DB = 12f

    val PRESETS: List<Pair<String, String>> = listOf(
        PRESET_OFF to "Off",
        PRESET_FLAT to "Flat",
        PRESET_BASS to "Bass",
        PRESET_TREBLE to "Treble",
        PRESET_VOCAL to "Vocal",
        PRESET_LOUDNESS to "Loud",
        PRESET_CUSTOM to "Custom",
    )

    /** Short on-device copy for the selected preset (no cloud profiles). */
    fun describe(preset: String): String = when (preset) {
        PRESET_OFF -> "EQ disabled — dry session output"
        PRESET_FLAT -> "Neutral bands (unity levels)"
        PRESET_BASS -> "Lift low end, ease highs"
        PRESET_TREBLE -> "Lift highs, ease lows"
        PRESET_VOCAL -> "Midrange bump for voices"
        PRESET_LOUDNESS -> "Mild smile curve (bass + treble)"
        PRESET_CUSTOM -> "Manual 10-band + preamp"
        else -> "AOSP Equalizer effect"
    }

    fun label(preset: String): String =
        PRESETS.firstOrNull { it.first == preset }?.second ?: preset

    const val ACTION_SET = "dev.voxhash.voxplayer.SET_EQ_PRESET"
    const val ACTION_SET_CUSTOM = "dev.voxhash.voxplayer.SET_EQ_CUSTOM"
    val CMD_SET: SessionCommand = SessionCommand(ACTION_SET, Bundle.EMPTY)
    val CMD_SET_CUSTOM: SessionCommand = SessionCommand(ACTION_SET_CUSTOM, Bundle.EMPTY)
    const val EXTRA_PRESET = "preset"
    const val EXTRA_BANDS = "bands_db"
    const val EXTRA_PREAMP = "preamp_db"
    const val EXTRA_SNAP = "snap_bands"

    fun normalize(preset: String): String =
        preset.takeIf { p -> PRESETS.any { it.first == p } } ?: PRESET_OFF

    fun clampDb(v: Float): Float = v.coerceIn(GAIN_MIN_DB, GAIN_MAX_DB)

    fun clampPreamp(v: Float): Float = v.coerceIn(PREAMP_MIN_DB, PREAMP_MAX_DB)

    fun zeroBands(): FloatArray = FloatArray(BAND_COUNT)

    fun bandsForPreset(preset: String): FloatArray {
        val id = normalize(preset)
        if (id == PRESET_OFF || id == PRESET_FLAT) return zeroBands()
        if (id == PRESET_CUSTOM) return zeroBands()
        val shape: (Int) -> Float = when (id) {
            PRESET_BASS -> { i ->
                val t = i / (BAND_COUNT - 1f)
                ((1f - t) * 0.85f - t * 0.15f)
            }
            PRESET_TREBLE -> { i ->
                val t = i / (BAND_COUNT - 1f)
                (t * 0.85f - (1f - t) * 0.1f)
            }
            PRESET_VOCAL -> { i ->
                val t = i / (BAND_COUNT - 1f)
                (1f - abs(t - 0.45f) * 2.2f)
            }
            PRESET_LOUDNESS -> { i ->
                val t = i / (BAND_COUNT - 1f)
                (0.55f * (1f - 4f * (t - 0.5f) * (t - 0.5f)) + 0.25f)
            }
            else -> { _ -> 0f }
        }
        return FloatArray(BAND_COUNT) { i ->
            clampDb(shape(i).coerceIn(-1f, 1f) * GAIN_MAX_DB)
        }
    }

    /** Neighbor pull when Snap bands is on (VLC-style adjacent follow). */
    fun withSnap(bands: FloatArray, index: Int, value: Float): FloatArray {
        val out = bands.copyOf(BAND_COUNT)
        val v = clampDb(value)
        out[index] = v
        if (index > 0) {
            out[index - 1] = clampDb(out[index - 1] * 0.55f + v * 0.45f)
        }
        if (index < BAND_COUNT - 1) {
            out[index + 1] = clampDb(out[index + 1] * 0.55f + v * 0.45f)
        }
        return out
    }

    fun loadPreset(context: Context): String =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_PRESET, PRESET_OFF)
            ?.let { normalize(it) }
            ?: PRESET_OFF

    fun savePreset(context: Context, preset: String) {
        val id = normalize(preset)
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_PRESET, id)
            .apply()
    }

    fun loadPreferred(context: Context): String? =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_PREFERRED, null)
            ?.takeIf { it.isNotBlank() }
            ?.let { normalize(it) }

    fun savePreferred(context: Context, preset: String) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_PREFERRED, normalize(preset))
            .apply()
    }

    fun clearPreferred(context: Context) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_PREFERRED)
            .apply()
    }

    /** Preferred pin if set, else last selected preset. */
    fun loadBootPreset(context: Context): String =
        loadPreferred(context) ?: loadPreset(context)

    fun loadBandsDb(context: Context): FloatArray {
        val raw = context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_BANDS, null)
        if (raw.isNullOrBlank()) {
            val preset = loadBootPreset(context)
            return if (preset == PRESET_CUSTOM) zeroBands() else bandsForPreset(preset)
        }
        return try {
            val arr = JSONArray(raw)
            FloatArray(BAND_COUNT) { i ->
                clampDb(arr.optDouble(i, 0.0).toFloat())
            }
        } catch (_: Exception) {
            zeroBands()
        }
    }

    fun saveBandsDb(context: Context, bands: FloatArray) {
        val arr = JSONArray()
        for (i in 0 until BAND_COUNT) {
            arr.put(clampDb(bands.getOrElse(i) { 0f }).toDouble())
        }
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_BANDS, arr.toString())
            .apply()
    }

    fun loadPreampDb(context: Context): Float =
        clampPreamp(
            context.applicationContext
                .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .getFloat(KEY_PREAMP, 0f),
        )

    fun savePreampDb(context: Context, db: Float) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putFloat(KEY_PREAMP, clampPreamp(db))
            .apply()
    }

    fun loadSnap(context: Context): Boolean =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean(KEY_SNAP, true)

    fun saveSnap(context: Context, snap: Boolean) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_SNAP, snap)
            .apply()
    }

    fun formatDb(db: Float): String {
        val v = (db * 10f).roundToInt() / 10f
        return when {
            v > 0.05f -> "+${v}dB"
            v < -0.05f -> "${v}dB"
            else -> "0dB"
        }
    }
}

class EqualizerApplier {
    private var equalizer: Equalizer? = null
    private var sessionId: Int = C.AUDIO_SESSION_ID_UNSET
    private var preset: String = EqualizerControl.PRESET_OFF
    private var bandsDb: FloatArray = EqualizerControl.zeroBands()
    private var preampDb: Float = 0f
    private var snapBands: Boolean = true

    fun setPreset(name: String) {
        preset = EqualizerControl.normalize(name)
        when (preset) {
            EqualizerControl.PRESET_OFF -> Unit
            EqualizerControl.PRESET_CUSTOM -> Unit // keep existing bands/preamp
            EqualizerControl.PRESET_FLAT -> bandsDb = EqualizerControl.zeroBands()
            else -> bandsDb = EqualizerControl.bandsForPreset(preset)
        }
        applyBands()
    }

    fun setCustom(bands: FloatArray, preampDb: Float, snap: Boolean) {
        preset = EqualizerControl.PRESET_CUSTOM
        bandsDb = FloatArray(EqualizerControl.BAND_COUNT) { i ->
            EqualizerControl.clampDb(bands.getOrElse(i) { 0f })
        }
        this.preampDb = EqualizerControl.clampPreamp(preampDb)
        snapBands = snap
        applyBands()
    }

    /** Load preset + custom bands/preamp/snap from prefs (cold start / reapply). */
    fun loadFromPrefs(context: Context) {
        preset = EqualizerControl.loadBootPreset(context)
        preampDb = EqualizerControl.loadPreampDb(context)
        snapBands = EqualizerControl.loadSnap(context)
        bandsDb = when (preset) {
            EqualizerControl.PRESET_OFF, EqualizerControl.PRESET_FLAT -> EqualizerControl.zeroBands()
            EqualizerControl.PRESET_CUSTOM -> EqualizerControl.loadBandsDb(context)
            else -> EqualizerControl.bandsForPreset(preset)
        }
        applyBands()
    }

    fun apply(player: Player) {
        if (player !is ExoPlayer) return
        val id = player.audioSessionId
        if (id == 0 || id == C.AUDIO_SESSION_ID_UNSET) return
        if (id != sessionId) {
            releaseEq()
            equalizer = try {
                Equalizer(0, id).also {
                    it.enabled = preset != EqualizerControl.PRESET_OFF
                }
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
            val hwBands = eq.numberOfBands.toInt()
            if (hwBands <= 0) return
            val min = eq.bandLevelRange[0]
            val max = eq.bandLevelRange[1]
            fun levelFromDb(db: Float): Short {
                val frac = (db / EqualizerControl.GAIN_MAX_DB).coerceIn(-1f, 1f)
                val span = if (frac >= 0f) max.toInt() else -min.toInt()
                return (frac * span).toInt().coerceIn(min.toInt(), max.toInt()).toShort()
            }
            for (i in 0 until hwBands) {
                val band = i.toShort()
                val centerMilliHz = try {
                    eq.getCenterFreq(band)
                } catch (_: Exception) {
                    0
                }
                val centerHz = if (centerMilliHz > 0) centerMilliHz / 1000f else {
                    EqualizerControl.BAND_HZ[
                        (i * (EqualizerControl.BAND_COUNT - 1) / (hwBands - 1).coerceAtLeast(1))
                            .coerceIn(0, EqualizerControl.BAND_COUNT - 1),
                    ]
                }
                val uiDb = interpolateUiDb(centerHz) + preampDb
                eq.setBandLevel(band, levelFromDb(uiDb))
            }
        } catch (e: Exception) {
            Log.w(TAG, "equalizer apply failed", e)
        }
    }

    /** Map hardware center freq onto the 10 UI band gains (log-frequency lerp). */
    private fun interpolateUiDb(freqHz: Float): Float {
        val f = freqHz.coerceAtLeast(1f)
        val hz = EqualizerControl.BAND_HZ
        if (f <= hz.first()) return bandsDb.first()
        if (f >= hz.last()) return bandsDb.last()
        for (i in 0 until hz.lastIndex) {
            if (f >= hz[i] && f <= hz[i + 1]) {
                val logA = ln(hz[i].toDouble())
                val logB = ln(hz[i + 1].toDouble())
                val logF = ln(f.toDouble())
                val t = ((logF - logA) / (logB - logA)).toFloat().coerceIn(0f, 1f)
                return bandsDb[i] * (1f - t) + bandsDb[i + 1] * t
            }
        }
        return 0f
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
