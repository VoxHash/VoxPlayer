package dev.voxhash.voxplayer.companion

import android.content.Intent
import android.os.Bundle
import android.util.Log
import androidx.annotation.OptIn
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.analytics.AnalyticsListener
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService
import androidx.media3.session.SessionResult
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture

/**
 * Hosts ExoPlayer + MediaSession so local audio/video can continue when the
 * activity is backgrounded (lock screen / other apps / Quest panel unfocused).
 *
 * GrapheneOS / battery note: this is a standard ``mediaPlayback`` foreground
 * service with a system media notification. Aggressive battery restrictions or
 * force-stop still end playback — we do not use proprietary keep-alive SDKs.
 *
 * Playback resumption: last item + position are stored locally; headset /
 * [androidx.media3.session.MediaButtonReceiver] can restart via
 * [MediaSession.Callback.onPlaybackResumption] after process death.
 *
 * Volume: desktop-parity 0–200% via [LocalVolume] + AOSP LoudnessEnhancer.
 */
class PlaybackService : MediaSessionService() {
    private var mediaSession: MediaSession? = null
    private lateinit var queueStore: PlaybackQueueStore
    private val volumeApplier = LocalVolumeApplier()
    private var volumePercent: Int = LocalVolume.DEFAULT_PERCENT
    private var volumeMuted: Boolean = false

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
            applyVolume()
        }
    }

    @OptIn(UnstableApi::class)
    private val sessionCallback = object : MediaSession.Callback {
        override fun onConnect(
            session: MediaSession,
            controller: MediaSession.ControllerInfo,
        ): MediaSession.ConnectionResult {
            val cmds = MediaSession.ConnectionResult.DEFAULT_SESSION_COMMANDS.buildUpon()
                .add(LocalVolume.CMD_SET)
                .build()
            return MediaSession.ConnectionResult.accept(
                cmds,
                MediaSession.ConnectionResult.DEFAULT_PLAYER_COMMANDS,
            )
        }

        override fun onCustomCommand(
            session: MediaSession,
            controller: MediaSession.ControllerInfo,
            customCommand: androidx.media3.session.SessionCommand,
            args: Bundle,
        ): ListenableFuture<SessionResult> {
            if (customCommand.customAction == LocalVolume.ACTION_SET) {
                volumePercent = args.getInt(LocalVolume.EXTRA_PERCENT, volumePercent).coerceIn(0, 200)
                volumeMuted = args.getBoolean(LocalVolume.EXTRA_MUTED, volumeMuted)
                LocalVolume.save(this@PlaybackService, volumePercent, volumeMuted)
                applyVolume()
                return Futures.immediateFuture(SessionResult(SessionResult.RESULT_SUCCESS))
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
        volumePercent = LocalVolume.loadPercent(this)
        volumeMuted = LocalVolume.loadMuted(this)
        val player = ExoPlayer.Builder(this)
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(C.USAGE_MEDIA)
                    .setContentType(C.AUDIO_CONTENT_TYPE_MUSIC)
                    .build(),
                /* handleAudioFocus = */ true,
            )
            .setHandleAudioBecomingNoisy(true)
            .build()
        player.repeatMode = Player.REPEAT_MODE_OFF
        player.addListener(persistListener)
        player.addAnalyticsListener(
            object : AnalyticsListener {
                override fun onAudioSessionIdChanged(
                    eventTime: AnalyticsListener.EventTime,
                    audioSessionId: Int,
                ) {
                    applyVolume()
                }
            },
        )
        mediaSession = MediaSession.Builder(this, player)
            .setId("voxplayer-local")
            .setCallback(sessionCallback)
            .build()
        applyVolume()
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
        persistQueue()
        volumeApplier.release()
        mediaSession?.run {
            player.removeListener(persistListener)
            player.release()
            release()
            mediaSession = null
        }
        super.onDestroy()
    }

    private fun applyVolume() {
        val player = mediaSession?.player ?: return
        volumeApplier.apply(player, volumePercent, volumeMuted)
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
    }
}
