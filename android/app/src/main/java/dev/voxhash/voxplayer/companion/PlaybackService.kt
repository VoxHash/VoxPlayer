package dev.voxhash.voxplayer.companion

import android.content.Intent
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.annotation.OptIn
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.analytics.AnalyticsListener
import androidx.media3.session.CommandButton
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService
import androidx.media3.session.SessionResult
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture

/**
 * Hosts ExoPlayer + MediaSession so local audio/video can continue when the
 * activity is backgrounded (lock screen / other apps / Quest panel unfocused).
 *
 * Headset / Car (no GMS Auto): Media3 maps headset media keys; we advertise
 * ±15s seek media-button preferences for Bluetooth AVRCP / System UI.
 *
 * Quest / route edge cases: [AudioDeviceCallback] re-applies the preferred
 * sink (or falls back to system default when it disconnects) and re-attaches
 * volume/EQ after session or device changes.
 */
class PlaybackService : MediaSessionService() {
    private var mediaSession: MediaSession? = null
    private lateinit var queueStore: PlaybackQueueStore
    private val volumeApplier = LocalVolumeApplier()
    private lateinit var routeApplier: AudioRouteApplier
    private val equalizerApplier = EqualizerApplier()
    private var volumePercent: Int = LocalVolume.DEFAULT_PERCENT
    private var volumeMuted: Boolean = false
    private var preferredDeviceId: Int = AudioRoute.DEFAULT_DEVICE_ID
    private var eqPreset: String = EqualizerControl.PRESET_OFF
    private var audioManager: AudioManager? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    private val deviceCallback = object : AudioDeviceCallback() {
        override fun onAudioDevicesAdded(addedDevices: Array<out AudioDeviceInfo>) {
            Log.i(TAG, "audio devices added count=${addedDevices.size}")
            mainHandler.post {
                // Preferred sink may have just (re)appeared — re-apply routing.
                applyAudioChain()
                notifyDevicesChanged()
            }
        }

        override fun onAudioDevicesRemoved(removedDevices: Array<out AudioDeviceInfo>) {
            Log.i(TAG, "audio devices removed count=${removedDevices.size}")
            mainHandler.post {
                val removedIds = removedDevices.map { it.id }.toSet()
                if (preferredDeviceId != AudioRoute.DEFAULT_DEVICE_ID && preferredDeviceId in removedIds) {
                    Log.w(TAG, "preferred sink $preferredDeviceId gone — falling back to system default")
                    preferredDeviceId = AudioRoute.DEFAULT_DEVICE_ID
                    AudioRoute.savePreferredId(this@PlaybackService, preferredDeviceId)
                }
                applyAudioChain()
                notifyDevicesChanged()
            }
        }
    }

    private val persistListener = object : Player.Listener {
        override fun onIsPlayingChanged(isPlaying: Boolean) {
            persistQueue()
        }

        override fun onMediaItemTransition(mediaItem: androidx.media3.common.MediaItem?, reason: Int) {
            persistQueue()
        }

        override fun onPlaybackStateChanged(playbackState: Int) {
            if (playbackState == Player.STATE_ENDED || playbackState == Player.STATE_IDLE) {
                persistQueue()
            }
            applyAudioChain()
        }
    }

    @OptIn(UnstableApi::class)
    private val sessionCallback = object : MediaSession.Callback {
        override fun onConnect(
            session: MediaSession,
            controller: MediaSession.ControllerInfo,
        ): MediaSession.ConnectionResult {
            val sessionCmds = MediaSession.ConnectionResult.DEFAULT_SESSION_COMMANDS.buildUpon()
                .add(LocalVolume.CMD_SET)
                .add(AudioRoute.CMD_SET)
                .add(EqualizerControl.CMD_SET)
                .add(AudioRoute.CMD_REAPPLY)
                .build()
            val playerCmds = MediaSession.ConnectionResult.DEFAULT_PLAYER_COMMANDS.buildUpon()
                .add(Player.COMMAND_SEEK_BACK)
                .add(Player.COMMAND_SEEK_FORWARD)
                .add(Player.COMMAND_SEEK_TO_NEXT)
                .add(Player.COMMAND_SEEK_TO_PREVIOUS)
                .add(Player.COMMAND_SEEK_TO_NEXT_MEDIA_ITEM)
                .add(Player.COMMAND_SEEK_TO_PREVIOUS_MEDIA_ITEM)
                .build()
            return MediaSession.ConnectionResult.accept(sessionCmds, playerCmds)
        }

        override fun onCustomCommand(
            session: MediaSession,
            controller: MediaSession.ControllerInfo,
            customCommand: androidx.media3.session.SessionCommand,
            args: Bundle,
        ): ListenableFuture<SessionResult> {
            when (customCommand.customAction) {
                LocalVolume.ACTION_SET -> {
                    volumePercent = args.getInt(LocalVolume.EXTRA_PERCENT, volumePercent).coerceIn(0, 200)
                    volumeMuted = args.getBoolean(LocalVolume.EXTRA_MUTED, volumeMuted)
                    LocalVolume.save(this@PlaybackService, volumePercent, volumeMuted)
                    applyAudioChain()
                    return Futures.immediateFuture(SessionResult(SessionResult.RESULT_SUCCESS))
                }
                AudioRoute.ACTION_SET -> {
                    preferredDeviceId = args.getInt(AudioRoute.EXTRA_DEVICE_ID, preferredDeviceId)
                    AudioRoute.savePreferredId(this@PlaybackService, preferredDeviceId)
                    applyAudioChain()
                    return Futures.immediateFuture(SessionResult(SessionResult.RESULT_SUCCESS))
                }
                EqualizerControl.ACTION_SET -> {
                    eqPreset = args.getString(EqualizerControl.EXTRA_PRESET, eqPreset)
                        ?: EqualizerControl.PRESET_OFF
                    EqualizerControl.savePreset(this@PlaybackService, eqPreset)
                    equalizerApplier.setPreset(eqPreset)
                    applyAudioChain()
                    return Futures.immediateFuture(SessionResult(SessionResult.RESULT_SUCCESS))
                }
                AudioRoute.ACTION_REAPPLY -> {
                    // Quest panel refocus / activity resume — reload prefs and re-bind effects.
                    volumePercent = LocalVolume.loadPercent(this@PlaybackService)
                    volumeMuted = LocalVolume.loadMuted(this@PlaybackService)
                    preferredDeviceId = AudioRoute.loadPreferredId(this@PlaybackService)
                    eqPreset = EqualizerControl.loadPreset(this@PlaybackService)
                    equalizerApplier.setPreset(eqPreset)
                    applyAudioChain()
                    return Futures.immediateFuture(SessionResult(SessionResult.RESULT_SUCCESS))
                }
            }
            return Futures.immediateFuture(SessionResult(SessionResult.RESULT_ERROR_NOT_SUPPORTED))
        }

        override fun onPlaybackResumption(
            mediaSession: MediaSession,
            controller: MediaSession.ControllerInfo,
        ): ListenableFuture<MediaSession.MediaItemsWithStartPosition> {
            val restored = queueStore.toMediaItemsWithStartPosition()
            return if (restored != null && restored.mediaItems.isNotEmpty()) {
                Log.i(TAG, "onPlaybackResumption items=${restored.mediaItems.size} pos=${restored.startPositionMs}")
                Futures.immediateFuture(restored)
            } else {
                Log.w(TAG, "onPlaybackResumption: nothing stored")
                Futures.immediateFailedFuture(IllegalStateException("No resumable media"))
            }
        }
    }

    @OptIn(UnstableApi::class)
    override fun onCreate() {
        super.onCreate()
        queueStore = PlaybackQueueStore(this)
        routeApplier = AudioRouteApplier(this)
        volumePercent = LocalVolume.loadPercent(this)
        volumeMuted = LocalVolume.loadMuted(this)
        preferredDeviceId = AudioRoute.loadPreferredId(this)
        eqPreset = EqualizerControl.loadPreset(this)
        equalizerApplier.setPreset(eqPreset)

        audioManager = getSystemService(AUDIO_SERVICE) as AudioManager
        audioManager?.registerAudioDeviceCallback(deviceCallback, mainHandler)

        val player = ExoPlayer.Builder(this)
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(C.USAGE_MEDIA)
                    .setContentType(C.AUDIO_CONTENT_TYPE_MUSIC)
                    .build(),
                /* handleAudioFocus = */ true,
            )
            .setHandleAudioBecomingNoisy(true)
            .setSeekBackIncrementMs(SEEK_INCREMENT_MS)
            .setSeekForwardIncrementMs(SEEK_INCREMENT_MS)
            .build()
        player.repeatMode = Player.REPEAT_MODE_OFF
        player.addListener(persistListener)
        player.addAnalyticsListener(
            object : AnalyticsListener {
                override fun onAudioSessionIdChanged(
                    eventTime: AnalyticsListener.EventTime,
                    audioSessionId: Int,
                ) {
                    applyAudioChain()
                }
            },
        )

        val mediaButtons = listOf(
            CommandButton.Builder(CommandButton.ICON_SKIP_BACK_15)
                .setPlayerCommand(Player.COMMAND_SEEK_BACK)
                .setSlots(CommandButton.SLOT_BACK)
                .setDisplayName("Back 15s")
                .build(),
            CommandButton.Builder(CommandButton.ICON_SKIP_FORWARD_15)
                .setPlayerCommand(Player.COMMAND_SEEK_FORWARD)
                .setSlots(CommandButton.SLOT_FORWARD)
                .setDisplayName("Forward 15s")
                .build(),
        )

        mediaSession = MediaSession.Builder(this, player)
            .setId("voxplayer-local")
            .setCallback(sessionCallback)
            .setMediaButtonPreferences(mediaButtons)
            .build()
        applyAudioChain()
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? =
        mediaSession

    override fun onTaskRemoved(rootIntent: Intent?) {
        persistQueue()
        val player = mediaSession?.player
        if (player == null || !player.playWhenReady || player.mediaItemCount == 0) {
            stopSelf()
        }
    }

    override fun onDestroy() {
        try {
            audioManager?.unregisterAudioDeviceCallback(deviceCallback)
        } catch (_: Exception) {
        }
        persistQueue()
        volumeApplier.release()
        equalizerApplier.release()
        mediaSession?.run {
            player.removeListener(persistListener)
            player.release()
            release()
            mediaSession = null
        }
        super.onDestroy()
    }

    private fun applyAudioChain() {
        val player = mediaSession?.player ?: return
        // If preferred id is stale (not in current sinks), clear to default.
        if (preferredDeviceId != AudioRoute.DEFAULT_DEVICE_ID &&
            AudioRoute.findDevice(this, preferredDeviceId) == null
        ) {
            Log.w(TAG, "preferred sink $preferredDeviceId missing — system default")
            preferredDeviceId = AudioRoute.DEFAULT_DEVICE_ID
            AudioRoute.savePreferredId(this, preferredDeviceId)
        }
        volumeApplier.apply(player, volumePercent, volumeMuted)
        routeApplier.apply(player, preferredDeviceId)
        equalizerApplier.apply(player)
    }

    private fun notifyDevicesChanged() {
        sendBroadcast(
            Intent(AudioRoute.ACTION_DEVICES_CHANGED).setPackage(packageName),
        )
    }

    private fun persistQueue() {
        val player = mediaSession?.player ?: return
        if (player.mediaItemCount == 0 || player.currentMediaItem == null) {
            return
        }
        queueStore.saveFromPlayer(player)
    }

    companion object {
        private const val TAG = "VoxPlaybackService"
        private const val SEEK_INCREMENT_MS = 15_000L
    }
}
