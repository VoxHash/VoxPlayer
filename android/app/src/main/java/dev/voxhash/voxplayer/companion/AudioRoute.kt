package dev.voxhash.voxplayer.companion

import android.content.Context
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.annotation.OptIn
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.SessionCommand

/**
 * On-device sound output picker via [AudioManager] (no GMS / Google Cast).
 * Preferred device id is persisted; ``-1`` means system default routing.
 */
object AudioRoute {
    const val PREFS = "voxplayer_audio_route"
    const val KEY_DEVICE_ID = "device_id"
    const val DEFAULT_DEVICE_ID = -1

    const val ACTION_SET = "dev.voxhash.voxplayer.SET_AUDIO_DEVICE"
    val CMD_SET: SessionCommand = SessionCommand(ACTION_SET, Bundle.EMPTY)
    const val EXTRA_DEVICE_ID = "device_id"

    /** Quest / activity resume: reload prefs and re-bind route + effects. */
    const val ACTION_REAPPLY = "dev.voxhash.voxplayer.REAPPLY_AUDIO"
    val CMD_REAPPLY: SessionCommand = SessionCommand(ACTION_REAPPLY, Bundle.EMPTY)

    /** Broadcast when sinks are added/removed (package-scoped). */
    const val ACTION_DEVICES_CHANGED = "dev.voxhash.voxplayer.AUDIO_DEVICES_CHANGED"
    /** True when preferred sink vanished and routing fell back to system default. */
    const val EXTRA_ROUTE_FALLBACK = "route_fallback"
    const val EXTRA_FALLBACK_FROM = "fallback_from"

    data class Device(
        val id: Int,
        val name: String,
        val typeLabel: String,
        val type: Int,
        val isSink: Boolean,
    ) {
        /** UI group for clearer multi-output routing. */
        val routeGroup: String
            get() = when (type) {
                AudioDeviceInfo.TYPE_BUILTIN_SPEAKER,
                AudioDeviceInfo.TYPE_BUILTIN_EARPIECE,
                -> "This device"
                AudioDeviceInfo.TYPE_WIRED_HEADSET,
                AudioDeviceInfo.TYPE_WIRED_HEADPHONES,
                -> "Wired"
                AudioDeviceInfo.TYPE_BLUETOOTH_A2DP,
                AudioDeviceInfo.TYPE_BLUETOOTH_SCO,
                AudioDeviceInfo.TYPE_HEARING_AID,
                -> "Bluetooth"
                AudioDeviceInfo.TYPE_USB_DEVICE,
                AudioDeviceInfo.TYPE_USB_HEADSET,
                -> "USB"
                AudioDeviceInfo.TYPE_HDMI,
                AudioDeviceInfo.TYPE_HDMI_ARC,
                -> "Display"
                else -> "Other"
            }
    }

    fun loadPreferredId(context: Context): Int =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getInt(KEY_DEVICE_ID, DEFAULT_DEVICE_ID)

    fun savePreferredId(context: Context, id: Int) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_DEVICE_ID, id)
            .apply()
    }

    fun listOutputDevices(context: Context): List<Device> {
        val am = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val devices = am.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
        return devices.map { info ->
            Device(
                id = info.id,
                name = deviceName(info),
                typeLabel = typeLabel(info.type),
                type = info.type,
                isSink = true,
            )
        }.sortedWith(
            compareBy(
                { routeGroupOrder(it.routeGroup) },
                { it.typeLabel },
                { it.name },
            ),
        )
    }

    private fun routeGroupOrder(group: String): Int = when (group) {
        "This device" -> 0
        "Wired" -> 1
        "Bluetooth" -> 2
        "USB" -> 3
        "Display" -> 4
        else -> 5
    }

    fun findDevice(context: Context, id: Int): AudioDeviceInfo? {
        if (id == DEFAULT_DEVICE_ID) return null
        val am = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        return am.getDevices(AudioManager.GET_DEVICES_OUTPUTS).firstOrNull { it.id == id }
    }

    private fun deviceName(info: AudioDeviceInfo): String {
        val raw = if (Build.VERSION.SDK_INT >= 28) {
            info.productName?.toString()?.trim().orEmpty()
        } else {
            ""
        }
        return raw.ifBlank { typeLabel(info.type) }
    }

    private fun typeLabel(type: Int): String = when (type) {
        AudioDeviceInfo.TYPE_BUILTIN_SPEAKER -> "Speaker"
        AudioDeviceInfo.TYPE_BUILTIN_EARPIECE -> "Earpiece"
        AudioDeviceInfo.TYPE_WIRED_HEADSET -> "Wired headset"
        AudioDeviceInfo.TYPE_WIRED_HEADPHONES -> "Wired headphones"
        AudioDeviceInfo.TYPE_BLUETOOTH_A2DP -> "Bluetooth"
        AudioDeviceInfo.TYPE_BLUETOOTH_SCO -> "Bluetooth SCO"
        AudioDeviceInfo.TYPE_USB_DEVICE -> "USB"
        AudioDeviceInfo.TYPE_USB_HEADSET -> "USB headset"
        AudioDeviceInfo.TYPE_HDMI -> "HDMI"
        AudioDeviceInfo.TYPE_HDMI_ARC -> "HDMI ARC"
        AudioDeviceInfo.TYPE_LINE_ANALOG -> "Line out"
        AudioDeviceInfo.TYPE_LINE_DIGITAL -> "Digital out"
        AudioDeviceInfo.TYPE_DOCK -> "Dock"
        AudioDeviceInfo.TYPE_HEARING_AID -> "Hearing aid"
        else -> "Output"
    }
}

/** Applies preferred audio device on [ExoPlayer]. */
class AudioRouteApplier(private val context: Context) {
    @OptIn(UnstableApi::class)
    fun apply(player: Player, preferredDeviceId: Int) {
        if (player !is ExoPlayer) return
        val device = AudioRoute.findDevice(context, preferredDeviceId)
        try {
            player.setPreferredAudioDevice(device)
            Log.i(TAG, "preferredAudioDevice id=$preferredDeviceId name=${device?.productName}")
        } catch (e: Exception) {
            Log.w(TAG, "setPreferredAudioDevice failed", e)
        }
    }

    companion object {
        private const val TAG = "VoxAudioRoute"
    }
}
