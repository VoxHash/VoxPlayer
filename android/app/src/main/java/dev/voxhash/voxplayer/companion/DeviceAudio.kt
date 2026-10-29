package dev.voxhash.voxplayer.companion

import android.os.Build
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C

/**
 * Headset / panel audio helpers (Quest / GrapheneOS-honest, no GMS).
 *
 * Horizon Audio Service spatializes MEDIA tracks by default (`can_spatialize=true`).
 * Combined with [android.media.audiofx.LoudnessEnhancer] / Equalizer session churn on
 * seek / next / previous, that path can leave a continuous hiss until the track is
 * recreated. Prefer non-spatial media attributes on Quest-class devices.
 */
object DeviceAudio {
    fun isQuestLike(): Boolean {
        val model = Build.MODEL.orEmpty().lowercase()
        val manufacturer = Build.MANUFACTURER.orEmpty().lowercase()
        val product = Build.PRODUCT.orEmpty().lowercase()
        val device = Build.DEVICE.orEmpty().lowercase()
        return model.contains("quest") ||
            product.contains("quest") ||
            device.contains("eureka") ||
            device.contains("hollywood") ||
            manufacturer.contains("oculus") ||
            (manufacturer.contains("meta") && (model.contains("quest") || product.contains("horizon")))
    }

    /** Media3 audio attributes tuned for local FOSS playback on this device class. */
    fun mediaAttributes(): AudioAttributes {
        val builder = AudioAttributes.Builder()
            .setUsage(C.USAGE_MEDIA)
            .setContentType(C.AUDIO_CONTENT_TYPE_MUSIC)
        // API 32+ / Media3: keep 2D panel media out of volumetric spatialize on Quest.
        if (Build.VERSION.SDK_INT >= 32 && isQuestLike()) {
            builder.setSpatializationBehavior(C.SPATIALIZATION_BEHAVIOR_NEVER)
        }
        return builder.build()
    }
}
