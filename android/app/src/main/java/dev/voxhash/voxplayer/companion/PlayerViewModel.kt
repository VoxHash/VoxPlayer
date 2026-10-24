package dev.voxhash.voxplayer.companion

import android.Manifest
import android.app.Application
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import com.google.common.util.concurrent.ListenableFuture
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File

enum class AppTab { Local, Connect }

enum class RemoteLink { None, Wifi, Bluetooth }

data class QueueRow(
    val index: Int,
    val title: String,
    val artist: String,
    val isCurrent: Boolean,
)

data class PlayerUiState(
    val tab: AppTab = AppTab.Local,
    val localItems: List<LocalMediaItem> = emptyList(),
    val localFilter: String = "all", // all|audio|video
    val permissionNeeded: Boolean = false,
    val localTitle: String = "(nothing loaded)",
    val localArtist: String = "",
    val localAlbum: String = "",
    val localQueueIndex: Int = 0,
    val localQueueSize: Int = 0,
    val localQueue: List<QueueRow> = emptyList(),
    /** Player.REPEAT_MODE_OFF / ONE / ALL */
    val localRepeatMode: Int = Player.REPEAT_MODE_OFF,
    val localShuffle: Boolean = false,
    /** Desktop-parity logical volume 0–200 */
    val localVolume: Int = LocalVolume.DEFAULT_PERCENT,
    val localMuted: Boolean = false,
    val audioDevices: List<AudioRoute.Device> = emptyList(),
    val preferredAudioDeviceId: Int = AudioRoute.DEFAULT_DEVICE_ID,
    val eqPreset: String = EqualizerControl.PRESET_OFF,
    val sleepEndEpochMs: Long = 0L,
    val sleepRemainingLabel: String = "Off",
    val bookmarks: List<BookmarkStore.Bookmark> = emptyList(),
    val localPlaying: Boolean = false,
    val localPositionLabel: String = "0:00 / 0:00",
    val localIsVideo: Boolean = false,
    val playerReady: Boolean = false,
    val error: String = "",
    // Connect / desktop remote
    val connectOpen: Boolean = false,
    val scanning: Boolean = false,
    val discovered: List<DiscoveredDesktop> = emptyList(),
    val bondedDevices: List<BluetoothControl.BondedHint> = emptyList(),
    val remoteHost: String = "192.168.1.1",
    val remotePort: String = "17890",
    val remoteLink: RemoteLink = RemoteLink.None,
    val remoteConnected: Boolean = false,
    val remotePlaying: Boolean = false,
    val remoteTitle: String = "(desktop idle)",
    val remotePositionLabel: String = "0:00 / 0:00",
    val remoteVolume: Int = 50,
    val remoteVersion: String = "",
    val remoteLibrary: List<DaemonClient.LibraryItem> = emptyList(),
    val activeOutput: String = "This device",
    val syncedPlaylists: List<SyncStore.SyncedPlaylist> = emptyList(),
    val syncedFeeds: List<SyncStore.SyncedFeed> = emptyList(),
    val syncBusy: Boolean = false,
    val syncMessage: String = "",
)

class PlayerViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = app.getSharedPreferences("voxplayer", Context.MODE_PRIVATE)
    private val syncStore = SyncStore(app)
    private val queueStore = PlaybackQueueStore(app)
    private val bookmarkStore = BookmarkStore(app)
    private val bt = BluetoothControl(app)
    private val _state = MutableStateFlow(
        PlayerUiState(
            remoteHost = prefs.getString("host", "192.168.1.1") ?: "192.168.1.1",
            remotePort = prefs.getString("port", "17890") ?: "17890",
            localRepeatMode = prefs.getInt(PREF_REPEAT, Player.REPEAT_MODE_OFF),
            localShuffle = prefs.getBoolean(PREF_SHUFFLE, false),
            localVolume = LocalVolume.loadPercent(app),
            localMuted = LocalVolume.loadMuted(app),
            preferredAudioDeviceId = AudioRoute.loadPreferredId(app),
            eqPreset = EqualizerControl.loadPreset(app),
            sleepEndEpochMs = SleepTimer.loadEndEpochMs(app),
            sleepRemainingLabel = SleepTimer.remainingLabel(SleepTimer.loadEndEpochMs(app)),
            bookmarks = bookmarkStore.load(),
            syncedPlaylists = syncStore.loadPlaylists(),
            syncedFeeds = syncStore.loadPodcasts(),
        ),
    )
    val state: StateFlow<PlayerUiState> = _state.asStateFlow()

    private val _player = MutableStateFlow<Player?>(null)
    val player: Player? get() = _player.value
    val playerFlow: StateFlow<Player?> = _player.asStateFlow()

    private var controllerFuture: ListenableFuture<MediaController>? = null
    private var remotePoll: Job? = null
    private var localTick: Job? = null
    private var pendingPlay: (() -> Unit)? = null
    private val devicesReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                AudioRoute.ACTION_DEVICES_CHANGED -> {
                    refreshAudioDevices()
                    _state.update {
                        it.copy(preferredAudioDeviceId = AudioRoute.loadPreferredId(getApplication()))
                    }
                }
                SleepTimer.ACTION_FIRED -> {
                    _state.update {
                        it.copy(sleepEndEpochMs = 0L, sleepRemainingLabel = "Off", localPlaying = false)
                    }
                }
            }
        }
    }

    private val playerListener = object : Player.Listener {
        override fun onIsPlayingChanged(isPlaying: Boolean) {
            _state.update {
                it.copy(
                    localPlaying = isPlaying,
                    activeOutput = if (isPlaying) "This device" else it.activeOutput,
                )
            }
        }

        override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
            player?.let { syncUiFromPlayer(it) }
            player?.let { queueStore.saveFromPlayer(it) }
        }

        override fun onRepeatModeChanged(repeatMode: Int) {
            prefs.edit().putInt(PREF_REPEAT, repeatMode).apply()
            _state.update { it.copy(localRepeatMode = repeatMode) }
        }

        override fun onShuffleModeEnabledChanged(shuffleModeEnabled: Boolean) {
            prefs.edit().putBoolean(PREF_SHUFFLE, shuffleModeEnabled).apply()
            _state.update { it.copy(localShuffle = shuffleModeEnabled) }
            player?.let { syncUiFromPlayer(it) }
        }

        override fun onTimelineChanged(timeline: androidx.media3.common.Timeline, reason: Int) {
            player?.let { syncUiFromPlayer(it) }
            player?.let { queueStore.saveFromPlayer(it) }
        }
    }

    init {
        connectLocalPlayer()
        refreshAudioDevices()
        registerDevicesReceiver()
        localTick = viewModelScope.launch {
            while (isActive) {
                refreshLocalClock()
                delay(500)
            }
        }
    }

    private fun registerDevicesReceiver() {
        val app = getApplication<Application>()
        val filter = IntentFilter().apply {
            addAction(AudioRoute.ACTION_DEVICES_CHANGED)
            addAction(SleepTimer.ACTION_FIRED)
        }
        try {
            if (Build.VERSION.SDK_INT >= 33) {
                app.registerReceiver(devicesReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
            } else {
                @Suppress("UnspecifiedRegisterReceiverFlag")
                app.registerReceiver(devicesReceiver, filter)
            }
        } catch (e: Exception) {
            Log.w(TAG, "registerDevicesReceiver failed", e)
        }
    }

    private fun connectLocalPlayer() {
        val app = getApplication<Application>()
        val token = SessionToken(app, ComponentName(app, PlaybackService::class.java))
        val future = MediaController.Builder(app, token).buildAsync()
        controllerFuture = future
        future.addListener(
            {
                try {
                    val controller = future.get()
                    controller.addListener(playerListener)
                    controller.repeatMode = prefs.getInt(PREF_REPEAT, Player.REPEAT_MODE_OFF)
                    controller.shuffleModeEnabled = prefs.getBoolean(PREF_SHUFFLE, false)
                    _player.value = controller
                    syncUiFromPlayer(controller)
                    pushLocalVolumeToService()
                    setPreferredAudioDevice(_state.value.preferredAudioDeviceId)
                    setEqPreset(_state.value.eqPreset)
                    _state.update { it.copy(playerReady = true) }
                    pendingPlay?.invoke()
                    pendingPlay = null
                } catch (e: Exception) {
                    Log.e(TAG, "MediaController connect failed", e)
                    _state.update { it.copy(error = e.message ?: e.toString(), playerReady = false) }
                }
            },
            ContextCompat.getMainExecutor(app),
        )
    }

    private fun withPlayer(block: (Player) -> Unit) {
        val p = player
        if (p != null) {
            block(p)
        } else {
            pendingPlay = { player?.let(block) }
        }
    }

    fun setTab(tab: AppTab) = _state.update { it.copy(tab = tab) }

    fun openConnect(open: Boolean) {
        _state.update { it.copy(connectOpen = open) }
        if (open) {
            refreshBluetoothHints()
            scanDesktops()
        }
    }

    fun updateRemoteHost(v: String) = _state.update { it.copy(remoteHost = v.trim()) }
    fun updateRemotePort(v: String) = _state.update { it.copy(remotePort = v.trim()) }
    fun setLocalFilter(f: String) = _state.update { it.copy(localFilter = f) }

    fun hasMediaPermission(): Boolean {
        val ctx = getApplication<Application>()
        return if (Build.VERSION.SDK_INT >= 33) {
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.READ_MEDIA_AUDIO) == PackageManager.PERMISSION_GRANTED ||
                ContextCompat.checkSelfPermission(ctx, Manifest.permission.READ_MEDIA_VIDEO) == PackageManager.PERMISSION_GRANTED
        } else {
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.READ_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED
        }
    }

    fun hasBluetoothPermission(): Boolean {
        if (Build.VERSION.SDK_INT < 31) return true
        val ctx = getApplication<Application>()
        return ContextCompat.checkSelfPermission(ctx, Manifest.permission.BLUETOOTH_CONNECT) ==
            PackageManager.PERMISSION_GRANTED
    }

    fun reloadLocalLibrary() {
        viewModelScope.launch {
            if (!hasMediaPermission()) {
                _state.update { it.copy(permissionNeeded = true) }
                return@launch
            }
            _state.update { it.copy(permissionNeeded = false) }
            val ctx = getApplication<Application>()
            val items = withContext(Dispatchers.IO) {
                LocalMediaStore.loadAudio(ctx) + LocalMediaStore.loadVideo(ctx)
            }
            _state.update { it.copy(localItems = items, error = "") }
        }
    }

    private fun mediaItemFromLocal(item: LocalMediaItem): MediaItem =
        MediaItem.Builder()
            .setUri(item.uri)
            .setMediaId("${if (item.isVideo) "v" else "a"}:${item.id}")
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(item.title)
                    .setArtist(item.artist.ifBlank { "VoxPlayer" })
                    .apply {
                        if (item.album.isNotBlank()) setAlbumTitle(item.album)
                        setMediaType(
                            if (item.isVideo) MediaMetadata.MEDIA_TYPE_VIDEO
                            else MediaMetadata.MEDIA_TYPE_MUSIC,
                        )
                    }
                    .setIsPlayable(true)
                    .build(),
            )
            .build()

    private fun mediaItem(
        uri: Uri,
        title: String,
        artist: String = "",
        album: String = "",
        isVideo: Boolean = false,
    ): MediaItem =
        MediaItem.Builder()
            .setUri(uri)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(title)
                    .setArtist(artist.ifBlank { "VoxPlayer" })
                    .apply {
                        if (album.isNotBlank()) setAlbumTitle(album)
                        setMediaType(
                            if (isVideo) MediaMetadata.MEDIA_TYPE_VIDEO
                            else MediaMetadata.MEDIA_TYPE_MUSIC,
                        )
                    }
                    .setIsPlayable(true)
                    .build(),
            )
            .build()

    private fun filteredLibrary(): List<LocalMediaItem> {
        val s = _state.value
        return when (s.localFilter) {
            "audio" -> s.localItems.filter { !it.isVideo }
            "video" -> s.localItems.filter { it.isVideo }
            else -> s.localItems
        }
    }

    fun playLocal(item: LocalMediaItem) {
        // Gapless queue: filtered library as Media3 playlist, start at the tapped item.
        // Same-kind continuity when filter is "all" (audio→audio / video→video from tap).
        val pool = filteredLibrary().let { list ->
            if (sFilterIsAll()) list.filter { it.isVideo == item.isVideo } else list
        }
        val start = pool.indexOfFirst { it.id == item.id && it.isVideo == item.isVideo }
            .let { if (it >= 0) it else 0 }
        val queue = if (pool.isEmpty()) listOf(item) else pool
        val startIndex = start.coerceIn(0, queue.lastIndex)
        withPlayer { p ->
            p.setMediaItems(queue.map { mediaItemFromLocal(it) }, startIndex, /* startPositionMs = */ 0L)
            p.prepare()
            p.play()
            queueStore.saveQueue(
                queue.map {
                    PlaybackQueueStore.Entry(
                        uri = it.uri.toString(),
                        title = it.title,
                        artist = it.artist,
                        album = it.album,
                        isVideo = it.isVideo,
                    )
                },
                startIndex,
                0L,
            )
        }
        val current = queue[startIndex]
        _state.update {
            it.copy(
                localTitle = current.title,
                localArtist = current.artist,
                localAlbum = current.album,
                localQueueIndex = startIndex,
                localQueueSize = queue.size,
                localIsVideo = current.isVideo,
                localPlaying = true,
                activeOutput = "This device",
                tab = AppTab.Local,
                connectOpen = false,
            )
        }
    }

    private fun sFilterIsAll(): Boolean = _state.value.localFilter == "all"

    fun playUri(uri: Uri, title: String = uri.lastPathSegment ?: "Media", isVideo: Boolean = true) {
        withPlayer { p ->
            p.setMediaItems(listOf(mediaItem(uri, title, isVideo = isVideo)), 0, 0L)
            p.prepare()
            p.play()
            queueStore.save(uri.toString(), title, 0L, isVideo)
        }
        _state.update {
            it.copy(
                localTitle = title,
                localArtist = "",
                localAlbum = "",
                localQueueIndex = 0,
                localQueueSize = 1,
                localIsVideo = isVideo,
                localPlaying = true,
                activeOutput = "This device",
            )
        }
    }

    fun playSyncedEpisode(ep: SyncStore.SyncedEpisode) {
        val url = ep.enclosureUrl.trim()
        if (url.isBlank()) {
            _state.update { it.copy(error = "Episode has no enclosure URL") }
            return
        }
        playUri(Uri.parse(url), ep.title, isVideo = false)
    }

    fun localPlayPause() {
        withPlayer { p -> if (p.isPlaying) p.pause() else p.play() }
    }

    fun localStop() {
        withPlayer {
            it.stop()
            it.clearMediaItems()
        }
        queueStore.clear()
        _state.update {
            it.copy(
                localPlaying = false,
                localTitle = "(nothing loaded)",
                localArtist = "",
                localAlbum = "",
                localQueueIndex = 0,
                localQueueSize = 0,
                localQueue = emptyList(),
            )
        }
    }

    fun localNext() {
        withPlayer { p ->
            if (p.hasNextMediaItem()) {
                p.seekToNextMediaItem()
            } else {
                p.seekTo((p.currentPosition + 15_000).coerceAtLeast(0L))
            }
        }
    }

    fun localPrev() {
        withPlayer { p ->
            if (p.currentPosition > 3_000L) {
                p.seekTo(0L)
            } else if (p.hasPreviousMediaItem()) {
                p.seekToPreviousMediaItem()
            } else {
                p.seekTo(0L)
            }
        }
    }

    fun cycleLocalRepeat() {
        withPlayer { p ->
            val next = when (p.repeatMode) {
                Player.REPEAT_MODE_OFF -> Player.REPEAT_MODE_ALL
                Player.REPEAT_MODE_ALL -> Player.REPEAT_MODE_ONE
                else -> Player.REPEAT_MODE_OFF
            }
            p.repeatMode = next
            prefs.edit().putInt(PREF_REPEAT, next).apply()
            _state.update { it.copy(localRepeatMode = next) }
        }
    }

    fun toggleLocalShuffle() {
        withPlayer { p ->
            val enabled = !p.shuffleModeEnabled
            p.shuffleModeEnabled = enabled
            prefs.edit().putBoolean(PREF_SHUFFLE, enabled).apply()
            _state.update { it.copy(localShuffle = enabled) }
            syncUiFromPlayer(p)
        }
    }

    fun moveQueueItem(from: Int, to: Int) {
        withPlayer { p ->
            if (from < 0 || to < 0 || from >= p.mediaItemCount || to >= p.mediaItemCount || from == to) {
                return@withPlayer
            }
            p.moveMediaItem(from, to)
            queueStore.saveFromPlayer(p)
            syncUiFromPlayer(p)
        }
    }

    fun removeQueueItem(index: Int) {
        withPlayer { p ->
            if (index < 0 || index >= p.mediaItemCount) return@withPlayer
            p.removeMediaItem(index)
            if (p.mediaItemCount == 0) {
                queueStore.clear()
                _state.update {
                    it.copy(
                        localPlaying = false,
                        localTitle = "(nothing loaded)",
                        localArtist = "",
                        localAlbum = "",
                        localQueueIndex = 0,
                        localQueueSize = 0,
                        localQueue = emptyList(),
                    )
                }
            } else {
                queueStore.saveFromPlayer(p)
                syncUiFromPlayer(p)
            }
        }
    }

    fun playQueueIndex(index: Int) {
        withPlayer { p ->
            if (index < 0 || index >= p.mediaItemCount) return@withPlayer
            p.seekTo(index, 0L)
            p.play()
        }
    }

    fun setLocalVolume(percent: Int) {
        val pct = percent.coerceIn(0, 200)
        val unmute = pct > 0 && _state.value.localMuted
        val muted = if (unmute) false else _state.value.localMuted
        _state.update { it.copy(localVolume = pct, localMuted = muted) }
        LocalVolume.save(getApplication(), pct, muted)
        pushLocalVolumeToService()
    }

    fun localVolUp() = setLocalVolume(_state.value.localVolume + 5)

    fun localVolDown() = setLocalVolume(_state.value.localVolume - 5)

    fun toggleLocalMute() {
        val muted = !_state.value.localMuted
        _state.update { it.copy(localMuted = muted) }
        LocalVolume.save(getApplication(), _state.value.localVolume, muted)
        pushLocalVolumeToService()
    }

    private fun pushLocalVolumeToService() {
        val controller = player as? MediaController ?: return
        val args = Bundle().apply {
            putInt(LocalVolume.EXTRA_PERCENT, _state.value.localVolume)
            putBoolean(LocalVolume.EXTRA_MUTED, _state.value.localMuted)
        }
        try {
            controller.sendCustomCommand(LocalVolume.CMD_SET, args)
        } catch (e: Exception) {
            Log.w(TAG, "SET_LOCAL_VOLUME failed", e)
        }
    }

    fun refreshAudioDevices() {
        val ctx = getApplication<Application>()
        val devices = try {
            AudioRoute.listOutputDevices(ctx)
        } catch (e: Exception) {
            Log.w(TAG, "listOutputDevices failed", e)
            emptyList()
        }
        _state.update { it.copy(audioDevices = devices) }
    }

    fun setPreferredAudioDevice(deviceId: Int) {
        _state.update { it.copy(preferredAudioDeviceId = deviceId) }
        AudioRoute.savePreferredId(getApplication(), deviceId)
        val controller = player as? MediaController ?: return
        val args = Bundle().apply { putInt(AudioRoute.EXTRA_DEVICE_ID, deviceId) }
        try {
            controller.sendCustomCommand(AudioRoute.CMD_SET, args)
        } catch (e: Exception) {
            Log.w(TAG, "SET_AUDIO_DEVICE failed", e)
        }
    }

    fun setEqPreset(preset: String) {
        val id = preset.takeIf { p -> EqualizerControl.PRESETS.any { it.first == p } }
            ?: EqualizerControl.PRESET_OFF
        _state.update { it.copy(eqPreset = id) }
        EqualizerControl.savePreset(getApplication(), id)
        val controller = player as? MediaController ?: return
        val args = Bundle().apply { putString(EqualizerControl.EXTRA_PRESET, id) }
        try {
            controller.sendCustomCommand(EqualizerControl.CMD_SET, args)
        } catch (e: Exception) {
            Log.w(TAG, "SET_EQ_PRESET failed", e)
        }
    }

    /** Quest panel refocus / activity resume: refresh sinks and re-bind audio chain. */
    fun reapplyLocalAudio() {
        refreshAudioDevices()
        _state.update {
            it.copy(
                localVolume = LocalVolume.loadPercent(getApplication()),
                localMuted = LocalVolume.loadMuted(getApplication()),
                preferredAudioDeviceId = AudioRoute.loadPreferredId(getApplication()),
                eqPreset = EqualizerControl.loadPreset(getApplication()),
            )
        }
        pushLocalVolumeToService()
        val controller = player as? MediaController ?: return
        try {
            controller.sendCustomCommand(AudioRoute.CMD_REAPPLY, Bundle.EMPTY)
        } catch (e: Exception) {
            Log.w(TAG, "REAPPLY_AUDIO failed", e)
        }
    }

    private fun queueRowsFromPlayer(p: Player): List<QueueRow> {
        if (p.mediaItemCount <= 0) return emptyList()
        val current = p.currentMediaItemIndex
        return buildList {
            for (i in 0 until p.mediaItemCount) {
                val item = p.getMediaItemAt(i)
                val md = item.mediaMetadata
                val title = md.title?.toString()
                    ?: item.localConfiguration?.uri?.lastPathSegment
                    ?: "Item ${i + 1}"
                val artist = md.artist?.toString().orEmpty().let { if (it == "VoxPlayer") "" else it }
                add(QueueRow(index = i, title = title, artist = artist, isCurrent = i == current))
            }
        }
    }

    private fun syncUiFromPlayer(p: Player) {
        val queue = queueRowsFromPlayer(p)
        val item = p.currentMediaItem
        if (item != null) {
            val md = item.mediaMetadata
            val title = md.title?.toString()
                ?: item.localConfiguration?.uri?.lastPathSegment
                ?: "(resumed)"
            val artist = md.artist?.toString().orEmpty().let { if (it == "VoxPlayer") "" else it }
            val album = md.albumTitle?.toString().orEmpty()
            val isVideo = md.mediaType == MediaMetadata.MEDIA_TYPE_VIDEO
                || md.mediaType == MediaMetadata.MEDIA_TYPE_MOVIE
                || queueStore.load()?.current?.isVideo == true
            _state.update {
                it.copy(
                    localTitle = title,
                    localArtist = artist,
                    localAlbum = album,
                    localQueueIndex = p.currentMediaItemIndex.coerceAtLeast(0),
                    localQueueSize = p.mediaItemCount.coerceAtLeast(0),
                    localQueue = queue,
                    localRepeatMode = p.repeatMode,
                    localShuffle = p.shuffleModeEnabled,
                    localIsVideo = isVideo,
                    localPlaying = p.isPlaying,
                    activeOutput = if (p.isPlaying) "This device" else it.activeOutput,
                )
            }
            return
        }
        val snap = queueStore.load() ?: return
        val cur = snap.current ?: return
        _state.update {
            it.copy(
                localTitle = cur.title,
                localArtist = cur.artist,
                localAlbum = cur.album,
                localQueueIndex = snap.index,
                localQueueSize = snap.entries.size,
                localQueue = snap.entries.mapIndexed { i, e ->
                    QueueRow(i, e.title, e.artist, i == snap.index)
                },
                localIsVideo = cur.isVideo,
            )
        }
    }

    fun localSeekBy(ms: Long) {
        withPlayer { p ->
            val pos = (p.currentPosition + ms).coerceAtLeast(0L)
            p.seekTo(pos)
        }
    }

    private fun refreshLocalClock() {
        val p = player ?: return
        val pos = p.currentPosition.coerceAtLeast(0L)
        val dur = p.duration.coerceAtLeast(0L).let { if (it < 0) 0 else it }
        val sleepEnd = _state.value.sleepEndEpochMs.let { end ->
            if (end > 0L && end <= System.currentTimeMillis()) 0L else end
        }
        _state.update {
            it.copy(
                localPlaying = p.isPlaying,
                localPositionLabel = "${fmt(pos)} / ${fmt(dur)}",
                sleepEndEpochMs = sleepEnd,
                sleepRemainingLabel = SleepTimer.remainingLabel(sleepEnd),
            )
        }
        // Auto-save resume bookmark ~every 5s while playing (desktop companion parity).
        if (p.isPlaying && pos >= 1_500L && System.currentTimeMillis() / 5_000L != lastBookmarkAutosaveBucket) {
            lastBookmarkAutosaveBucket = System.currentTimeMillis() / 5_000L
            autosaveBookmark(p)
        }
    }

    private var lastBookmarkAutosaveBucket = -1L

    private fun autosaveBookmark(p: Player) {
        val item = p.currentMediaItem ?: return
        val uri = item.localConfiguration?.uri?.toString()
            ?: item.requestMetadata.mediaUri?.toString()
            ?: return
        val title = item.mediaMetadata.title?.toString()
            ?: Uri.parse(uri).lastPathSegment
            ?: "Bookmark"
        val isVideo = _state.value.localIsVideo
        bookmarkStore.upsert(uri, title, p.currentPosition.coerceAtLeast(0L), isVideo)
        _state.update { it.copy(bookmarks = bookmarkStore.load()) }
    }

    fun setSleepTimerMinutes(minutes: Int) {
        val end = if (minutes <= 0) 0L else System.currentTimeMillis() + minutes * 60_000L
        SleepTimer.saveEndEpochMs(getApplication(), end)
        _state.update {
            it.copy(sleepEndEpochMs = end, sleepRemainingLabel = SleepTimer.remainingLabel(end))
        }
        val controller = player as? MediaController ?: return
        val args = Bundle().apply { putInt(SleepTimer.EXTRA_MINUTES, minutes.coerceAtLeast(0)) }
        try {
            controller.sendCustomCommand(SleepTimer.CMD_SET, args)
        } catch (e: Exception) {
            Log.w(TAG, "SET_SLEEP_TIMER failed", e)
        }
    }

    fun clearSleepTimer() = setSleepTimerMinutes(0)

    fun bookmarkNow() {
        val p = player ?: return
        autosaveBookmark(p)
    }

    fun playBookmark(bm: BookmarkStore.Bookmark) {
        withPlayer { p ->
            p.setMediaItems(
                listOf(
                    MediaItem.Builder()
                        .setUri(bm.uri)
                        .setMediaMetadata(
                            MediaMetadata.Builder()
                                .setTitle(bm.title)
                                .setArtist("VoxPlayer")
                                .setMediaType(
                                    if (bm.isVideo) MediaMetadata.MEDIA_TYPE_VIDEO
                                    else MediaMetadata.MEDIA_TYPE_MUSIC,
                                )
                                .setIsPlayable(true)
                                .build(),
                        )
                        .build(),
                ),
                /* startIndex = */ 0,
                bm.positionMs.coerceAtLeast(0L),
            )
            p.prepare()
            p.play()
            queueStore.save(bm.uri, bm.title, bm.positionMs, bm.isVideo)
        }
        _state.update {
            it.copy(
                localTitle = bm.title,
                localArtist = "",
                localAlbum = "",
                localIsVideo = bm.isVideo,
                localQueueIndex = 0,
                localQueueSize = 1,
                localPlaying = true,
                activeOutput = "This device",
                tab = AppTab.Local,
            )
        }
    }

    fun removeBookmark(uri: String) {
        bookmarkStore.remove(uri)
        _state.update { it.copy(bookmarks = bookmarkStore.load()) }
    }

    fun clearBookmarks() {
        bookmarkStore.clear()
        _state.update { it.copy(bookmarks = emptyList()) }
    }

    fun scanDesktops() {
        viewModelScope.launch {
            _state.update { it.copy(scanning = true, error = "") }
            try {
                val list = LanDiscovery.scan(getApplication())
                _state.update { it.copy(discovered = list, scanning = false) }
            } catch (e: Exception) {
                _state.update { it.copy(scanning = false, error = e.message ?: e.toString()) }
            }
        }
    }

    fun refreshBluetoothHints() {
        val devices = if (hasBluetoothPermission()) {
            try {
                bt.bondedDevices()
            } catch (_: Exception) {
                emptyList()
            }
        } else {
            emptyList()
        }
        _state.update { it.copy(bondedDevices = devices.take(16)) }
    }

    fun connectDesktop(host: String, port: Int) {
        bt.disconnect()
        _state.update {
            it.copy(
                remoteHost = host,
                remotePort = port.toString(),
                connectOpen = false,
                tab = AppTab.Connect,
                remoteLink = RemoteLink.Wifi,
                activeOutput = "Desktop · $host",
            )
        }
        prefs.edit().putString("host", host).putString("port", port.toString()).apply()
        withPlayer { if (it.isPlaying) it.pause() }
        startRemotePoll()
    }

    fun connectManual() {
        val s = _state.value
        val port = s.remotePort.toIntOrNull() ?: 17890
        connectDesktop(s.remoteHost, port)
    }

    fun connectBluetooth(address: String, name: String) {
        if (!hasBluetoothPermission()) {
            _state.update { it.copy(error = "Bluetooth permission required") }
            Log.e(TAG, "BT connect denied: permission")
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(error = "", syncMessage = "Connecting Bluetooth…") }
            try {
                remotePoll?.cancel()
                val hello = withContext(Dispatchers.IO) {
                    bt.connect(address)
                }
                Log.i(TAG, "BT connected to $address hello=$hello")
                withPlayer { if (it.isPlaying) it.pause() }
                _state.update {
                    it.copy(
                        connectOpen = false,
                        tab = AppTab.Connect,
                        remoteLink = RemoteLink.Bluetooth,
                        remoteConnected = true,
                        activeOutput = "Desktop · BT · $name",
                        syncMessage = "",
                        error = "",
                    )
                }
                withContext(Dispatchers.IO) {
                    val st = bt.status()
                    Log.i(TAG, "BT status ok playing=${st.optBoolean("playing")} v=${st.optString("version")}")
                    val pl = bt.playlists()
                    Log.i(TAG, "BT playlists ok count=${pl.optJSONArray("playlists")?.length() ?: 0}")
                }
                startRemotePoll()
            } catch (e: Exception) {
                Log.e(TAG, "BT connect failed to $address", e)
                bt.disconnect()
                _state.update {
                    it.copy(
                        remoteConnected = false,
                        remoteLink = RemoteLink.None,
                        error = e.message ?: e.toString(),
                        syncMessage = "",
                    )
                }
            }
        }
    }

    fun disconnectRemote() {
        remotePoll?.cancel()
        remotePoll = null
        bt.disconnect()
        _state.update {
            it.copy(
                remoteConnected = false,
                remoteLink = RemoteLink.None,
                activeOutput = "This device",
                remoteLibrary = emptyList(),
            )
        }
    }

    private fun startRemotePoll() {
        remotePoll?.cancel()
        remotePoll = viewModelScope.launch {
            refreshRemoteLibrary()
            while (isActive) {
                refreshRemoteOnce()
                delay(1000)
            }
        }
    }

    private fun client(): DaemonClient {
        val s = _state.value
        return DaemonClient("http://${s.remoteHost}:${s.remotePort}")
    }

    private fun runRemote(blockHttp: (DaemonClient) -> Unit, blockBt: (BluetoothControl) -> Unit) {
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    if (bt.connected) blockBt(bt) else blockHttp(client())
                }
                refreshRemoteOnce()
            } catch (e: Exception) {
                _state.update { it.copy(error = e.message ?: e.toString(), remoteConnected = false) }
            }
        }
    }

    fun remotePlayPause() = runRemote({ it.playPause() }, { it.playPause() })
    fun remoteStop() = runRemote({ it.stop() }, { it.stop() })
    fun remoteNext() = runRemote({ it.next() }, { it.next() })
    fun remotePrev() = runRemote({ it.previous() }, { it.previous() })
    fun remoteSeekBack() = runRemote({ it.seekRelative(-5000) }, { it.seekRelative(-5000) })
    fun remoteSeekFwd() = runRemote({ it.seekRelative(5000) }, { it.seekRelative(5000) })
    fun remoteVolDown() = runRemote(
        { c -> c.volume((_state.value.remoteVolume - 5).coerceAtLeast(0)) },
        { c -> c.volume((_state.value.remoteVolume - 5).coerceAtLeast(0)) },
    )
    fun remoteVolUp() = runRemote(
        { c -> c.volume((_state.value.remoteVolume + 5).coerceAtMost(200)) },
        { c -> c.volume((_state.value.remoteVolume + 5).coerceAtMost(200)) },
    )
    fun remoteOpen(path: String) = runRemote({ it.open(path) }, {
        it.command("open", JSONObject().put("path", path))
    })

    fun refreshRemoteLibrary() = viewModelScope.launch {
        try {
            val items = withContext(Dispatchers.IO) {
                if (bt.connected) {
                    val obj = bt.library(200)
                    val arr = obj.optJSONArray("items") ?: org.json.JSONArray()
                    buildList {
                        for (i in 0 until arr.length()) {
                            val it = arr.optJSONObject(i) ?: continue
                            val path = it.optString("path", "")
                            if (path.isBlank()) continue
                            add(
                                DaemonClient.LibraryItem(
                                    path,
                                    it.optString("title", path.substringAfterLast('/')),
                                ),
                            )
                        }
                    }
                } else {
                    client().library(200, 0).items
                }
            }
            _state.update { it.copy(remoteLibrary = items) }
        } catch (e: Exception) {
            _state.update { it.copy(error = e.message ?: e.toString()) }
        }
    }

    fun syncFromDesktop() {
        viewModelScope.launch {
            _state.update { it.copy(syncBusy = true, syncMessage = "Pulling playlists & podcasts…", error = "") }
            try {
                val (playlists, feeds) = withContext(Dispatchers.IO) {
                    if (bt.connected) {
                        val pl = SyncStore.playlistsFromJson(bt.playlists())
                        val pod = SyncStore.podcastsFromJson(bt.podcasts())
                        syncStore.savePlaylists(pl)
                        syncStore.savePodcasts(pod)
                        pl to pod
                    } else {
                        val c = client()
                        val pl = c.playlists()
                        val pod = c.podcasts()
                        syncStore.savePlaylists(pl)
                        syncStore.savePodcasts(pod)
                        pl to pod
                    }
                }
                _state.update {
                    it.copy(
                        syncBusy = false,
                        syncedPlaylists = syncStore.loadPlaylists(),
                        syncedFeeds = syncStore.loadPodcasts(),
                        syncMessage = "Synced ${playlists.size} playlist(s), ${feeds.size} feed(s)",
                    )
                }
            } catch (e: Exception) {
                _state.update {
                    it.copy(
                        syncBusy = false,
                        syncMessage = "",
                        error = e.message ?: e.toString(),
                    )
                }
            }
        }
    }

    private suspend fun refreshRemoteOnce() {
        try {
            val st = withContext(Dispatchers.IO) {
                if (bt.connected) {
                    val obj = bt.status()
                    DaemonClient.Status(
                        playing = obj.optBoolean("playing", false),
                        path = obj.optString("path", ""),
                        positionMs = obj.optLong("position_ms", 0L),
                        durationMs = obj.optLong("duration_ms", 0L),
                        volumePercent = obj.optInt("volume_percent", 50),
                        version = obj.optString("version", ""),
                        raw = obj,
                    )
                } else {
                    client().status()
                }
            }
            val name = File(st.path).name.ifBlank { "(desktop idle)" }
            _state.update {
                val link = if (bt.connected) RemoteLink.Bluetooth else RemoteLink.Wifi
                val output = if (bt.connected) {
                    it.activeOutput.takeIf { o -> o.startsWith("Desktop · BT") } ?: "Desktop · BT"
                } else {
                    "Desktop · ${it.remoteHost}"
                }
                it.copy(
                    remoteConnected = true,
                    remoteLink = link,
                    error = "",
                    remotePlaying = st.playing,
                    remoteTitle = name,
                    remotePositionLabel = "${fmt(st.positionMs)} / ${fmt(st.durationMs)}",
                    remoteVolume = st.volumePercent,
                    remoteVersion = st.version,
                    activeOutput = output,
                )
            }
        } catch (e: Exception) {
            _state.update { it.copy(remoteConnected = false, error = e.message ?: e.toString()) }
        }
    }

    private fun fmt(ms: Long): String {
        val sec = (ms / 1000).coerceAtLeast(0)
        return "%d:%02d".format(sec / 60, sec % 60)
    }

    override fun onCleared() {
        remotePoll?.cancel()
        localTick?.cancel()
        bt.disconnect()
        try {
            getApplication<Application>().unregisterReceiver(devicesReceiver)
        } catch (_: Exception) {
        }
        _player.value?.removeListener(playerListener)
        val future = controllerFuture
        if (future != null) {
            MediaController.releaseFuture(future)
        } else {
            (_player.value as? MediaController)?.release()
        }
        _player.value = null
        super.onCleared()
    }

    companion object {
        private const val TAG = "VoxPlayerBT"
        private const val PREF_REPEAT = "local_repeat_mode"
        private const val PREF_SHUFFLE = "local_shuffle"
    }
}
