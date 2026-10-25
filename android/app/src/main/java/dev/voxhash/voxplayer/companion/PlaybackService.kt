package dev.voxhash.voxplayer.companion

import android.app.PendingIntent
import android.content.Intent
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.net.Uri
import android.os.Build
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
 * ±15s seek media-button preferences for Bluetooth AVRCP / System UI, plus
 * overflow Previous / Next / Bookmark / Speed for richer notifications.
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
    private var sleepEndEpochMs: Long = 0L
    private var crossfadeEnabled: Boolean = true
    private var skipSilence: Boolean = false
    private var fadeMs: Long = CrossfadeControl.DEFAULT_FADE_MS
    private var playbackSpeed: Float = PlaybackSpeed.DEFAULT
    private val crossfadeApplier = CrossfadeApplier()
    private var audioManager: AudioManager? = null
    private val mainHandler = Handler(Looper.getMainLooper())
    private val sleepTick = object : Runnable {
        override fun run() {
            tickSleepTimer()
        }
    }

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
                var fallbackFrom: String? = null
                if (preferredDeviceId != AudioRoute.DEFAULT_DEVICE_ID && preferredDeviceId in removedIds) {
                    val gone = removedDevices.firstOrNull { it.id == preferredDeviceId }
                    fallbackFrom = gone?.let { info ->
                        val raw = if (android.os.Build.VERSION.SDK_INT >= 28) {
                            info.productName?.toString()?.trim().orEmpty()
                        } else {
                            ""
                        }
                        raw.ifBlank { "Headset" }
                    } ?: "Headset"
                    Log.w(TAG, "preferred sink $preferredDeviceId gone — falling back to system default")
                    preferredDeviceId = AudioRoute.DEFAULT_DEVICE_ID
                    AudioRoute.savePreferredId(this@PlaybackService, preferredDeviceId)
                }
                applyAudioChain()
                notifyDevicesChanged(fallbackFrom = fallbackFrom)
            }
        }
    }

    private val persistListener = object : Player.Listener {
        override fun onIsPlayingChanged(isPlaying: Boolean) {
            persistQueue()
            notifyWidget()
        }

        override fun onMediaItemTransition(mediaItem: androidx.media3.common.MediaItem?, reason: Int) {
            persistQueue()
            notifyWidget()
            // Soft fade-in on auto / repeat advances — reduces clicks across mixed codecs.
            if (reason == Player.MEDIA_ITEM_TRANSITION_REASON_AUTO ||
                reason == Player.MEDIA_ITEM_TRANSITION_REASON_REPEAT
            ) {
                val player = mediaSession?.player ?: return
                val target = LocalVolume.playerVolume(volumePercent, muted = false)
                crossfadeApplier.onAutoTransition(
                    player,
                    crossfadeEnabled,
                    target,
                    volumeMuted,
                    fadeMs,
                )
            }
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
                .add(SleepTimer.CMD_SET)
                .add(CrossfadeControl.CMD_SET)
                .add(PlaybackSpeed.CMD_SET)
                .add(NotificationActions.CMD_BOOKMARK)
                .add(NotificationActions.CMD_CYCLE_SPEED)
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
                    playbackSpeed = PlaybackSpeed.load(this@PlaybackService)
                    mediaSession?.player?.let { PlaybackSpeed.apply(it, playbackSpeed) }
                    applyAudioChain()
                    return Futures.immediateFuture(SessionResult(SessionResult.RESULT_SUCCESS))
                }
                SleepTimer.ACTION_SET -> {
                    val minutes = args.getInt(SleepTimer.EXTRA_MINUTES, -1)
                    if (minutes == 0) {
                        clearSleepTimer(restoreVolume = true)
                    } else {
                        val end = if (minutes > 0) {
                            System.currentTimeMillis() + minutes * 60_000L
                        } else {
                            args.getLong(SleepTimer.EXTRA_END_EPOCH_MS, 0L)
                        }
                        scheduleSleepTimer(end)
                    }
                    return Futures.immediateFuture(SessionResult(SessionResult.RESULT_SUCCESS))
                }
                CrossfadeControl.ACTION_SET -> {
                    crossfadeEnabled = args.getBoolean(CrossfadeControl.EXTRA_CROSSFADE, crossfadeEnabled)
                    skipSilence = args.getBoolean(CrossfadeControl.EXTRA_SKIP_SILENCE, skipSilence)
                    fadeMs = CrossfadeControl.normalizeFadeMs(
                        args.getLong(CrossfadeControl.EXTRA_FADE_MS, fadeMs),
                    )
                    CrossfadeControl.save(
                        this@PlaybackService,
                        crossfadeEnabled,
                        skipSilence,
                        fadeMs,
                    )
                    applySkipSilence()
                    return Futures.immediateFuture(SessionResult(SessionResult.RESULT_SUCCESS))
                }
                PlaybackSpeed.ACTION_SET -> {
                    playbackSpeed = PlaybackSpeed.normalize(
                        args.getFloat(PlaybackSpeed.EXTRA_SPEED, playbackSpeed),
                    )
                    PlaybackSpeed.save(this@PlaybackService, playbackSpeed)
                    mediaSession?.player?.let { PlaybackSpeed.apply(it, playbackSpeed) }
                    return Futures.immediateFuture(SessionResult(SessionResult.RESULT_SUCCESS))
                }
                NotificationActions.ACTION_BOOKMARK -> {
                    bookmarkFromNotification()
                    return Futures.immediateFuture(SessionResult(SessionResult.RESULT_SUCCESS))
                }
                NotificationActions.ACTION_CYCLE_SPEED -> {
                    cycleSpeedFromNotification()
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
        crossfadeEnabled = CrossfadeControl.loadCrossfade(this)
        skipSilence = CrossfadeControl.loadSkipSilence(this)
        fadeMs = CrossfadeControl.loadFadeMs(this)
        playbackSpeed = PlaybackSpeed.load(this)

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
        player.skipSilenceEnabled = skipSilence
        PlaybackSpeed.apply(player, playbackSpeed)
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

        val mediaButtons = buildMediaButtonPreferences()

        val openApp = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or
                if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0,
        )

        mediaSession = MediaSession.Builder(this, player)
            .setId("voxplayer-local")
            .setCallback(sessionCallback)
            .setMediaButtonPreferences(mediaButtons)
            .setSessionActivity(openApp)
            .build()
        applyAudioChain()
        val pendingSleep = SleepTimer.loadEndEpochMs(this)
        if (pendingSleep > 0L) scheduleSleepTimer(pendingSleep)
        notifyWidget()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            PlaybackWidgetProvider.ACTION_PLAY_PAUSE -> {
                val player = mediaSession?.player
                if (player != null) {
                    if (player.isPlaying) player.pause() else {
                        if (player.mediaItemCount == 0) {
                            // Cold start from widget: rely on Media3 playback resumption store.
                            player.prepare()
                        }
                        player.play()
                    }
                }
                notifyWidget()
            }
            PlaybackWidgetProvider.ACTION_PREV -> {
                mediaSession?.player?.seekToPreviousMediaItem()
                notifyWidget()
            }
            PlaybackWidgetProvider.ACTION_NEXT -> {
                mediaSession?.player?.seekToNextMediaItem()
                notifyWidget()
            }
        }
        return super.onStartCommand(intent, flags, startId)
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
        mainHandler.removeCallbacks(sleepTick)
        try {
            audioManager?.unregisterAudioDeviceCallback(deviceCallback)
        } catch (_: Exception) {
        }
        persistQueue()
        crossfadeApplier.release()
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

    private fun scheduleSleepTimer(endEpochMs: Long) {
        mainHandler.removeCallbacks(sleepTick)
        sleepEndEpochMs = if (endEpochMs > System.currentTimeMillis()) endEpochMs else 0L
        SleepTimer.saveEndEpochMs(this, sleepEndEpochMs)
        if (sleepEndEpochMs > 0L) {
            Log.i(TAG, "sleep timer until $sleepEndEpochMs")
            mainHandler.post(sleepTick)
        }
    }

    private fun clearSleepTimer(restoreVolume: Boolean) {
        mainHandler.removeCallbacks(sleepTick)
        sleepEndEpochMs = 0L
        SleepTimer.saveEndEpochMs(this, 0L)
        if (restoreVolume) {
            applyAudioChain()
        }
    }

    private fun tickSleepTimer() {
        if (sleepEndEpochMs <= 0L) return
        val now = System.currentTimeMillis()
        val left = sleepEndEpochMs - now
        if (left <= 0L) {
            fireSleepTimer()
            return
        }
        // Fade over the last ~30s by temporarily lowering ExoPlayer volume.
        if (left <= FADE_WINDOW_MS && !volumeMuted) {
            val player = mediaSession?.player
            if (player != null) {
                val base = LocalVolume.playerVolume(volumePercent, muted = false)
                val frac = (left.toFloat() / FADE_WINDOW_MS).coerceIn(0f, 1f)
                player.volume = base * frac
            }
        }
        mainHandler.postDelayed(sleepTick, SLEEP_TICK_MS)
    }

    private fun fireSleepTimer() {
        Log.i(TAG, "sleep timer fired — pausing")
        mediaSession?.player?.pause()
        clearSleepTimer(restoreVolume = true)
        sendBroadcast(Intent(SleepTimer.ACTION_FIRED).setPackage(packageName))
    }

    private fun applySkipSilence() {
        val player = mediaSession?.player as? ExoPlayer ?: return
        player.skipSilenceEnabled = skipSilence
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
        // Don't stomp an in-progress soft fade-in / sleep fade.
        if (!crossfadeApplier.isActive() && sleepEndEpochMs <= 0L) {
            volumeApplier.apply(player, volumePercent, volumeMuted)
        } else if (!crossfadeApplier.isActive()) {
            // Sleep timer may own volume; still attach enhancer/route when muted path needed.
            if (volumeMuted) volumeApplier.apply(player, volumePercent, true)
        }
        routeApplier.apply(player, preferredDeviceId)
        equalizerApplier.apply(player)
        applySkipSilence()
    }

    private fun notifyDevicesChanged(fallbackFrom: String? = null) {
        val intent = Intent(AudioRoute.ACTION_DEVICES_CHANGED).setPackage(packageName)
        if (!fallbackFrom.isNullOrBlank()) {
            intent.putExtra(AudioRoute.EXTRA_ROUTE_FALLBACK, true)
            intent.putExtra(AudioRoute.EXTRA_FALLBACK_FROM, fallbackFrom)
        }
        sendBroadcast(intent)
    }

    private fun persistQueue() {
        val player = mediaSession?.player ?: return
        if (player.mediaItemCount == 0 || player.currentMediaItem == null) {
            return
        }
        queueStore.saveFromPlayer(player)
    }

    private fun notifyWidget() {
        val player = mediaSession?.player
        val title = player?.currentMediaItem?.mediaMetadata?.title?.toString()
        val artist = player?.currentMediaItem?.mediaMetadata?.artist?.toString()
        PlaybackWidgetProvider.notify(
            this,
            title = title,
            subtitle = artist,
            playing = player?.isPlaying == true,
        )
    }

    @OptIn(UnstableApi::class)
    private fun buildMediaButtonPreferences(): List<CommandButton> = listOf(
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
        CommandButton.Builder(CommandButton.ICON_PREVIOUS)
            .setPlayerCommand(Player.COMMAND_SEEK_TO_PREVIOUS_MEDIA_ITEM)
            .setSlots(CommandButton.SLOT_OVERFLOW)
            .setDisplayName("Previous")
            .build(),
        CommandButton.Builder(CommandButton.ICON_NEXT)
            .setPlayerCommand(Player.COMMAND_SEEK_TO_NEXT_MEDIA_ITEM)
            .setSlots(CommandButton.SLOT_OVERFLOW)
            .setDisplayName("Next")
            .build(),
        CommandButton.Builder(CommandButton.ICON_BOOKMARK_UNFILLED)
            .setSessionCommand(NotificationActions.CMD_BOOKMARK)
            .setSlots(CommandButton.SLOT_OVERFLOW)
            .setDisplayName("Bookmark")
            .build(),
        CommandButton.Builder(CommandButton.ICON_UNDEFINED)
            .setCustomIconResId(android.R.drawable.ic_menu_recent_history)
            .setSessionCommand(NotificationActions.CMD_CYCLE_SPEED)
            .setSlots(CommandButton.SLOT_OVERFLOW)
            .setDisplayName("Speed")
            .build(),
    )

    private fun bookmarkFromNotification() {
        val player = mediaSession?.player ?: return
        val item = player.currentMediaItem ?: return
        val uri = item.localConfiguration?.uri?.toString()
            ?: item.requestMetadata.mediaUri?.toString()
            ?: return
        val title = item.mediaMetadata.title?.toString()
            ?: Uri.parse(uri).lastPathSegment
            ?: "Bookmark"
        val isVideo = item.mediaMetadata.mediaType ==
            androidx.media3.common.MediaMetadata.MEDIA_TYPE_VIDEO
        BookmarkStore(this).upsert(
            uri,
            title,
            player.currentPosition.coerceAtLeast(0L),
            isVideo,
        )
        Log.i(TAG, "notification bookmark uri=$uri pos=${player.currentPosition}")
    }

    private fun cycleSpeedFromNotification() {
        val options = PlaybackSpeed.OPTIONS.map { it.first }
        val idx = options.indexOfFirst { kotlin.math.abs(it - playbackSpeed) < 0.001f }
        val next = options[(idx + 1).coerceAtLeast(0) % options.size]
        playbackSpeed = PlaybackSpeed.normalize(next)
        PlaybackSpeed.save(this, playbackSpeed)
        mediaSession?.player?.let { PlaybackSpeed.apply(it, playbackSpeed) }
        Log.i(TAG, "notification speed → $playbackSpeed")
    }

    companion object {
        private const val TAG = "VoxPlaybackService"
        private const val SEEK_INCREMENT_MS = 15_000L
        private const val SLEEP_TICK_MS = 1_000L
        private const val FADE_WINDOW_MS = 30_000L
    }
}
