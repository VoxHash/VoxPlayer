package dev.voxhash.voxplayer.companion

import android.Manifest
import android.app.Application
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.ContentUris
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

/** Primary shell destinations (phone bottom bar / tablet rail) — Video · Audio · Browse · Lists · More. */
enum class PrimaryDest { Video, Audio, Browse, Lists, More }

enum class RemoteLink { None, Wifi, Bluetooth }

data class QueueRow(
    val index: Int,
    val title: String,
    val artist: String,
    val isCurrent: Boolean,
    val uri: String = "",
)

data class PlayerUiState(
    val tab: AppTab = AppTab.Local,
    val localItems: List<LocalMediaItem> = emptyList(),
    val localFilter: String = "all", // all|audio|video|recent|top|week|month|lists
    /** When filter=audio: artists | albums | tracks (MediaStore-grouped). */
    val audioFacet: String = "artists",
    /** Browse destination: SAF favorites + open folder listing. */
    val browseFavorites: List<BrowseStore.FavoriteFolder> = emptyList(),
    /** When set, Browse shows this folder's media rows (null = favorites index). */
    val browseFolderTitle: String = "",
    val browseFolderItems: List<LocalMediaItem> = emptyList(),
    /** Sticky preferred Home filter; empty = none (cold start uses preferred when set). */
    val localFilterPreferred: String = "",
    /** Case-insensitive title / artist / album substring (Home library + history facets). */
    val localSearchQuery: String = "",
    /** Last Home A–Z section letter (null = top). */
    val homeAzLetter: Char? = null,
    /** Home pull-to-refresh in progress. */
    val libraryRefreshing: Boolean = false,
    /** Long-press library card: track waiting for playlist pick (null = sheet closed). */
    val addToListPending: LocalPlaylistStore.Track? = null,
    /** When set, Add-to-list sheet hides this folder (copy to another list). */
    val addToListExcludePlaylistId: String? = null,
    val permissionNeeded: Boolean = false,
    val localTitle: String = "(nothing loaded)",
    val localArtist: String = "",
    val localAlbum: String = "",
    val localQueueIndex: Int = 0,
    val localQueueSize: Int = 0,
    val localQueue: List<QueueRow> = emptyList(),
    /** Player.REPEAT_MODE_OFF / ONE / ALL */
    val localRepeatMode: Int = Player.REPEAT_MODE_OFF,
    /** Sticky preferred repeat; -1 = none. */
    val localRepeatPreferred: Int = -1,
    val localShuffle: Boolean = false,
    /** Sticky preferred shuffle-on (long-press); false = no pin. */
    val localShufflePreferred: Boolean = false,
    /** Desktop-parity logical volume 0–200 */
    val localVolume: Int = LocalVolume.DEFAULT_PERCENT,
    val localMuted: Boolean = false,
    val audioDevices: List<AudioRoute.Device> = emptyList(),
    val preferredAudioDeviceId: Int = AudioRoute.DEFAULT_DEVICE_ID,
    /** Sticky preferred sink (type+name); survives disconnect / id churn. Empty name = none. */
    val audioPinType: Int = Int.MIN_VALUE,
    val audioPinName: String = "",
    val eqPreset: String = EqualizerControl.PRESET_OFF,
    /** Sticky preferred EQ preset id (empty = none). */
    val eqPreferredId: String = "",
    /** Custom 10-band gains in dB (−12…+12). */
    val eqBandsDb: List<Float> = List(EqualizerControl.BAND_COUNT) { 0f },
    val eqPreampDb: Float = 0f,
    val eqSnapBands: Boolean = true,
    val eqSheetOpen: Boolean = false,
    val sleepEndEpochMs: Long = 0L,
    val sleepRemainingLabel: String = "Off",
    /** Sticky preferred sleep duration minutes; 0 = none. */
    val sleepPreferredMinutes: Int = 0,
    val bookmarks: List<BookmarkStore.Bookmark> = emptyList(),
    /** Silent per-track resume hint shown after auto-seek (empty when none). */
    val resumeHint: String = "",
    val historyRecent: List<PlayHistoryStore.Entry> = emptyList(),
    val historyTop: List<PlayHistoryStore.Entry> = emptyList(),
    val historyWeek: PlayHistoryStore.PeriodFacet = PlayHistoryStore.PeriodFacet("This week", 0, 0, "", emptyList()),
    val historyMonth: PlayHistoryStore.PeriodFacet = PlayHistoryStore.PeriodFacet("This month", 0, 0, "", emptyList()),
    val localPlaylists: List<LocalPlaylistStore.Playlist> = emptyList(),
    /** When filter=lists, null = folder index; else browse that playlist id or smart:* */
    val listsBrowseId: String? = null,
    val lyricsSource: String = "",
    val lyricsTimed: Boolean = false,
    val lyricsLines: List<String> = emptyList(),
    val lyricsActiveIndex: Int = -1,
    val crossfadeEnabled: Boolean = true,
    val skipSilence: Boolean = false,
    val fadeMs: Long = CrossfadeControl.DEFAULT_FADE_MS,
    /** Sticky preferred fade length; -1 = none. */
    val fadeMsPreferred: Long = -1L,
    val playbackSpeed: Float = PlaybackSpeed.DEFAULT,
    /** Sticky preferred speed; NaN = none. */
    val playbackSpeedPreferred: Float = Float.NaN,
    val themeMode: ThemeMode = ThemeMode.Dark,
    /** Sticky preferred theme; null encoded as empty preferredThemeLabel. */
    val themePreferred: ThemeMode? = null,
    /** Multi-window / Quest panel / fold — for UI chrome (playback stays in service). */
    val multiWindow: Boolean = false,
    val foldSeparating: Boolean = false,
    /** Opt-in DLNA/UPnP cast (no GMS Cast). */
    val dlnaEnabled: Boolean = false,
    val dlnaBusy: Boolean = false,
    val dlnaMessage: String = "",
    val dlnaRenderers: List<DlnaCastControl.Renderer> = emptyList(),
    val dlnaSelectedId: String = "",
    /** Persisted preferred MediaRenderer id (empty = none). */
    val dlnaDefaultId: String = "",
    val localPlaying: Boolean = false,
    val localPositionLabel: String = "0:00 / 0:00",
    val localPositionMs: Long = 0L,
    val localDurationMs: Long = 0L,
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
    /** Short headset / toggle feedback (ephemeral status line). */
    val statusToast: String = "",
    /** First Clear tap arms confirmation; second clears with undo window. */
    val queueClearArmed: Boolean = false,
    val queueUndoAvailable: Boolean = false,
    /** Single Up-next row remove can be undone briefly. */
    val queueItemUndoAvailable: Boolean = false,
)

class PlayerViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = app.getSharedPreferences("voxplayer", Context.MODE_PRIVATE)
    private val syncStore = SyncStore(app)
    private val queueStore = PlaybackQueueStore(app)
    private val bookmarkStore = BookmarkStore(app)
    private val resumeStore = TrackResumeStore(app)
    private val historyStore = PlayHistoryStore(app)
    private val playlistStore = LocalPlaylistStore(app)
    private val bt = BluetoothControl(app)
    private val _state = MutableStateFlow(
        run {
            val audioPin = AudioRoute.loadPin(app)
            PlayerUiState(
                remoteHost = prefs.getString("host", "192.168.1.1") ?: "192.168.1.1",
                remotePort = prefs.getString("port", "17890") ?: "17890",
                localFilter = loadBootHomeFilter(),
                audioFacet = prefs.getString(PREF_AUDIO_FACET, "artists")
                    ?.takeIf { it in AUDIO_FACETS }
                    ?: "artists",
                browseFavorites = BrowseStore.loadFavorites(app),
                localFilterPreferred = prefs.getString(PREF_HOME_FILTER_PREFERRED, null)
                    ?.takeIf { it in HOME_FILTERS }
                    .orEmpty(),
                localSearchQuery = prefs.getString(PREF_HOME_SEARCH, "") ?: "",
                homeAzLetter = prefs.getString(PREF_HOME_AZ, null)?.firstOrNull(),
                localRepeatMode = loadBootRepeatMode(),
                localRepeatPreferred = loadPreferredRepeatMode() ?: -1,
                localShuffle = loadBootShuffle(),
                localShufflePreferred = prefs.getBoolean(PREF_SHUFFLE_PREFERRED, false),
                localVolume = LocalVolume.loadPercent(app),
                localMuted = LocalVolume.loadMuted(app),
                preferredAudioDeviceId = AudioRoute.loadPreferredId(app),
                audioPinType = audioPin?.type ?: Int.MIN_VALUE,
                audioPinName = audioPin?.name.orEmpty(),
                eqPreset = EqualizerControl.loadBootPreset(app),
                eqPreferredId = EqualizerControl.loadPreferred(app).orEmpty(),
                eqBandsDb = EqualizerControl.loadBandsDb(app).toList(),
                eqPreampDb = EqualizerControl.loadPreampDb(app),
                eqSnapBands = EqualizerControl.loadSnap(app),
                sleepEndEpochMs = SleepTimer.loadEndEpochMs(app),
                sleepRemainingLabel = SleepTimer.remainingLabel(SleepTimer.loadEndEpochMs(app)),
                sleepPreferredMinutes = SleepTimer.loadPreferredMinutes(app) ?: 0,
                bookmarks = bookmarkStore.load(),
                historyRecent = historyStore.recentlyPlayed(),
                historyTop = historyStore.mostPlayed(),
                historyWeek = historyStore.weekFacet(),
                historyMonth = historyStore.monthFacet(),
                localPlaylists = playlistStore.load(),
                crossfadeEnabled = CrossfadeControl.loadCrossfade(app),
                skipSilence = CrossfadeControl.loadSkipSilence(app),
                fadeMs = CrossfadeControl.loadBootFadeMs(app),
                fadeMsPreferred = CrossfadeControl.loadPreferredFadeMs(app) ?: -1L,
                playbackSpeed = PlaybackSpeed.loadBoot(app),
                playbackSpeedPreferred = PlaybackSpeed.loadPreferred(app) ?: Float.NaN,
                themeMode = ThemePrefs.loadBoot(app),
                themePreferred = ThemePrefs.loadPreferred(app),
                dlnaEnabled = DlnaCastControl.loadEnabled(app),
                dlnaDefaultId = DlnaCastControl.loadDefaultId(app),
                dlnaSelectedId = DlnaCastControl.loadDefaultId(app),
                syncedPlaylists = syncStore.loadPlaylists(),
                syncedFeeds = syncStore.loadPodcasts(),
            )
        },
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
                    val fellBack = intent?.getBooleanExtra(AudioRoute.EXTRA_ROUTE_FALLBACK, false) == true
                    val from = intent?.getStringExtra(AudioRoute.EXTRA_FALLBACK_FROM).orEmpty()
                        .ifBlank { "Headset" }
                    val prevPreferred = _state.value.preferredAudioDeviceId
                    val nextPreferred = AudioRoute.loadPreferredId(getApplication())
                    if (fellBack) {
                        val playing = _state.value.localPlaying
                        val vol = _state.value.localVolume
                        val ducked = playing && !_state.value.localMuted && vol > ROUTE_FALLBACK_VOLUME_CAP
                        if (ducked) {
                            setLocalVolume(ROUTE_FALLBACK_VOLUME_CAP)
                        }
                        _state.update {
                            it.copy(
                                preferredAudioDeviceId = nextPreferred,
                                statusToast = buildString {
                                    append(from)
                                    append(" disconnected · System default")
                                    if (ducked) append(" · volume capped at $ROUTE_FALLBACK_VOLUME_CAP%")
                                },
                            )
                        }
                        clearStatusToastLater(6_000L)
                    } else {
                        _state.update {
                            it.copy(preferredAudioDeviceId = nextPreferred)
                        }
                        if (prevPreferred != nextPreferred &&
                            nextPreferred == AudioRoute.DEFAULT_DEVICE_ID &&
                            prevPreferred != AudioRoute.DEFAULT_DEVICE_ID
                        ) {
                            _state.update {
                                it.copy(statusToast = "Audio route reset to System default")
                            }
                            clearStatusToastLater()
                        }
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
                    val bootRepeat = loadBootRepeatMode()
                    val bootShuffle = loadBootShuffle()
                    controller.repeatMode = bootRepeat
                    controller.shuffleModeEnabled = bootShuffle
                    prefs.edit()
                        .putInt(PREF_REPEAT, bootRepeat)
                        .putBoolean(PREF_SHUFFLE, bootShuffle)
                        .apply()
                    _state.update {
                        it.copy(
                            localRepeatMode = bootRepeat,
                            localRepeatPreferred = loadPreferredRepeatMode() ?: -1,
                            localShuffle = bootShuffle,
                            localShufflePreferred = prefs.getBoolean(PREF_SHUFFLE_PREFERRED, false),
                        )
                    }
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

    /** Bottom / rail primary destinations (GrapheneOS-friendly Material nav; no GMS). */
    fun setPrimaryDest(dest: PrimaryDest) {
        when (dest) {
            PrimaryDest.Video -> {
                setTab(AppTab.Local)
                setLocalFilter("video")
            }
            PrimaryDest.Audio -> {
                setTab(AppTab.Local)
                setLocalFilter("audio")
                // Keep last Artists/Albums/Tracks facet (defaults to artists).
            }
            PrimaryDest.Browse -> {
                setTab(AppTab.Local)
                setLocalFilter("browse")
                closeBrowseFolder()
            }
            PrimaryDest.Lists -> {
                setTab(AppTab.Local)
                setLocalFilter("lists")
            }
            PrimaryDest.More -> setTab(AppTab.Connect)
        }
    }

    fun openConnect(open: Boolean) {
        _state.update { it.copy(connectOpen = open) }
        if (open) {
            refreshBluetoothHints()
            scanDesktops()
        }
    }

    fun updateRemoteHost(v: String) = _state.update { it.copy(remoteHost = v.trim()) }
    fun updateRemotePort(v: String) = _state.update { it.copy(remotePort = v.trim()) }
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
            _state.update { it.copy(libraryRefreshing = true) }
            try {
                if (!hasMediaPermission()) {
                    _state.update { it.copy(permissionNeeded = true) }
                    return@launch
                }
                _state.update { it.copy(permissionNeeded = false) }
                val ctx = getApplication<Application>()
                val items = withContext(Dispatchers.IO) {
                    LocalMediaStore.loadAudio(ctx) + LocalMediaStore.loadVideo(ctx)
                }
                _state.update {
                    it.copy(
                        localItems = items,
                        error = "",
                        historyRecent = historyStore.recentlyPlayed(),
                        historyTop = historyStore.mostPlayed(),
                        historyWeek = historyStore.weekFacet(),
                        historyMonth = historyStore.monthFacet(),
                        localPlaylists = playlistStore.load(),
                        statusToast = "Library refreshed · ${items.size} items",
                    )
                }
                clearStatusToastLater()
            } finally {
                _state.update { it.copy(libraryRefreshing = false) }
            }
        }
    }

    private fun mediaItemFromLocal(item: LocalMediaItem): MediaItem =
        MediaItem.Builder()
            .setUri(item.uri)
            .setMediaId("${if (item.isVideo) "v" else "a"}:${item.id}")
            .setMediaMetadata(richMetadata(item))
            .build()

    /** Richer session metadata for Bluetooth AVRCP / System UI / car head units (no GMS Auto). */
    private fun richMetadata(item: LocalMediaItem): MediaMetadata {
        val artist = item.artist.ifBlank { "VoxPlayer" }
        return MediaMetadata.Builder()
            .setTitle(item.title)
            .setDisplayTitle(item.title)
            .setArtist(artist)
            .setSubtitle(listOf(artist, item.album).filter { it.isNotBlank() }.joinToString(" · "))
            .apply {
                if (item.album.isNotBlank()) setAlbumTitle(item.album)
                if (item.durationMs > 0L) setDurationMs(item.durationMs)
                if (!item.isVideo && item.albumId > 0L) {
                    setArtworkUri(
                        ContentUris.withAppendedId(
                            Uri.parse("content://media/external/audio/albumart"),
                            item.albumId,
                        ),
                    )
                }
                setMediaType(
                    if (item.isVideo) MediaMetadata.MEDIA_TYPE_VIDEO
                    else MediaMetadata.MEDIA_TYPE_MUSIC,
                )
            }
            .setIsPlayable(true)
            .build()
    }

    private fun mediaItem(
        uri: Uri,
        title: String,
        artist: String = "",
        album: String = "",
        isVideo: Boolean = false,
        durationMs: Long = 0L,
    ): MediaItem =
        MediaItem.Builder()
            .setUri(uri)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(title)
                    .setDisplayTitle(title)
                    .setArtist(artist.ifBlank { "VoxPlayer" })
                    .apply {
                        if (album.isNotBlank()) setAlbumTitle(album)
                        if (durationMs > 0L) setDurationMs(durationMs)
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
            "recent", "top", "week", "month", "lists" -> s.localItems // facets / lists play their own queues
            else -> s.localItems
        }
    }

    private fun refreshHistoryFacets() {
        _state.update {
            it.copy(
                historyRecent = historyStore.recentlyPlayed(),
                historyTop = historyStore.mostPlayed(),
                historyWeek = historyStore.weekFacet(),
                historyMonth = historyStore.monthFacet(),
            )
        }
    }

    private fun refreshPlaylists() {
        _state.update { it.copy(localPlaylists = playlistStore.load()) }
    }

    fun setLocalFilter(f: String) {
        val filter = if (f in HOME_FILTERS) f else "all"
        prefs.edit().putString(PREF_HOME_FILTER, filter).apply()
        _state.update {
            it.copy(
                localFilter = filter,
                listsBrowseId = if (filter == "lists") it.listsBrowseId else null,
                browseFolderTitle = if (filter == "browse") it.browseFolderTitle else "",
                browseFolderItems = if (filter == "browse") it.browseFolderItems else emptyList(),
            )
        }
    }

    /** Long-press: pin / clear preferred Home filter (restored on cold start). */
    fun setPreferredLocalFilter(f: String) {
        val filter = if (f in HOME_FILTERS) f else return
        if (_state.value.localFilterPreferred == filter) {
            prefs.edit().remove(PREF_HOME_FILTER_PREFERRED).apply()
            _state.update {
                it.copy(
                    localFilterPreferred = "",
                    statusToast = "Preferred Home filter cleared",
                )
            }
            clearStatusToastLater()
            return
        }
        prefs.edit().putString(PREF_HOME_FILTER_PREFERRED, filter).apply()
        setLocalFilter(filter)
        _state.update {
            it.copy(
                localFilterPreferred = filter,
                statusToast = "Preferred Home · ${homeFilterLabel(filter)}",
            )
        }
        clearStatusToastLater()
    }

    private fun loadBootHomeFilter(): String {
        val preferred = prefs.getString(PREF_HOME_FILTER_PREFERRED, null)?.takeIf { it in HOME_FILTERS }
        if (preferred != null) return preferred
        return prefs.getString(PREF_HOME_FILTER, "all")?.takeIf { it in HOME_FILTERS } ?: "all"
    }

    private fun homeFilterLabel(filter: String): String = when (filter) {
        "all" -> "All"
        "audio" -> "Audio"
        "video" -> "Video"
        "recent" -> "Recent"
        "top" -> "Top"
        "week" -> "Week"
        "month" -> "Month"
        "lists" -> "Lists"
        "browse" -> "Browse"
        else -> filter
    }

    fun closeBrowseFolder() {
        _state.update { it.copy(browseFolderTitle = "", browseFolderItems = emptyList()) }
    }

    /** Built-in MediaStore path shortcut (Download / Music / Movies / Podcasts). */
    fun openBrowseShortcut(label: String, pathHint: String) {
        val needle = pathHint.trim().trim('/').lowercase()
        val items = _state.value.localItems.filter { item ->
            val path = item.relativePath.replace('\\', '/').lowercase()
            path.startsWith("$needle/") || path == needle || path.contains("/$needle/")
        }.sortedWith(compareBy(String.CASE_INSENSITIVE_ORDER) { it.title })
        _state.update {
            it.copy(
                localFilter = "browse",
                browseFolderTitle = label,
                browseFolderItems = items,
                statusToast = if (items.isEmpty()) {
                    "No MediaStore items in $label — Add folder… or Open file"
                } else {
                    ""
                },
            )
        }
        if (items.isEmpty()) clearStatusToastLater()
        prefs.edit().putString(PREF_HOME_FILTER, "browse").apply()
    }

    /** Open a persisted SAF tree favorite and list audio/video children. */
    fun openBrowseFavorite(folder: BrowseStore.FavoriteFolder) {
        viewModelScope.launch(Dispatchers.IO) {
            val items = listSafMedia(Uri.parse(folder.treeUri))
            withContext(Dispatchers.Main) {
                _state.update {
                    it.copy(
                        localFilter = "browse",
                        browseFolderTitle = folder.label,
                        browseFolderItems = items,
                        statusToast = if (items.isEmpty()) {
                            "No media in ${folder.label}"
                        } else {
                            ""
                        },
                    )
                }
                if (items.isEmpty()) clearStatusToastLater()
                prefs.edit().putString(PREF_HOME_FILTER, "browse").apply()
            }
        }
    }

    /** Internal / primary volume: show all on-device MediaStore items as a storage listing. */
    fun openBrowseInternalStorage() {
        val items = _state.value.localItems
            .sortedWith(compareBy(String.CASE_INSENSITIVE_ORDER) { it.title })
        _state.update {
            it.copy(
                localFilter = "browse",
                browseFolderTitle = "Internal storage",
                browseFolderItems = items,
            )
        }
        prefs.edit().putString(PREF_HOME_FILTER, "browse").apply()
    }

    fun addBrowseFavorite(treeUri: Uri, label: String) {
        val app = getApplication<Application>()
        try {
            app.contentResolver.takePersistableUriPermission(
                treeUri,
                Intent.FLAG_GRANT_READ_URI_PERMISSION,
            )
        } catch (_: Exception) {
        }
        val display = label.ifBlank {
            treeUri.lastPathSegment?.substringAfterLast(':')?.replace("%2F", "/")?.substringAfterLast('/')
                ?: "Folder"
        }
        val next = BrowseStore.addFavorite(app, treeUri, display)
        _state.update {
            it.copy(
                browseFavorites = next,
                statusToast = "Favorite · $display",
            )
        }
        clearStatusToastLater()
        openBrowseFavorite(next.first { it.treeUri == treeUri.toString() })
    }

    fun removeBrowseFavorite(id: String) {
        val app = getApplication<Application>()
        val removed = _state.value.browseFavorites.find { it.id == id }
        if (removed != null) {
            try {
                app.contentResolver.releasePersistableUriPermission(
                    Uri.parse(removed.treeUri),
                    Intent.FLAG_GRANT_READ_URI_PERMISSION,
                )
            } catch (_: Exception) {
            }
        }
        val next = BrowseStore.removeFavorite(app, id)
        _state.update {
            it.copy(
                browseFavorites = next,
                statusToast = "Favorite removed",
                browseFolderTitle = if (it.browseFolderTitle == removed?.label) "" else it.browseFolderTitle,
                browseFolderItems = if (it.browseFolderTitle == removed?.label) emptyList() else it.browseFolderItems,
            )
        }
        clearStatusToastLater()
    }

    private fun listSafMedia(treeUri: Uri): List<LocalMediaItem> {
        val root = androidx.documentfile.provider.DocumentFile.fromTreeUri(getApplication(), treeUri)
            ?: return emptyList()
        val out = ArrayList<LocalMediaItem>()
        fun walk(dir: androidx.documentfile.provider.DocumentFile, depth: Int) {
            if (depth > 4 || out.size >= 400) return
            dir.listFiles().forEach { child ->
                if (out.size >= 400) return
                when {
                    child.isDirectory -> walk(child, depth + 1)
                    child.isFile -> {
                        val name = child.name ?: return@forEach
                        val mime = child.type.orEmpty()
                        val isVideo = mime.startsWith("video/") ||
                            name.substringAfterLast('.', "").lowercase() in VIDEO_EXTS
                        val isAudio = mime.startsWith("audio/") ||
                            name.substringAfterLast('.', "").lowercase() in AUDIO_EXTS
                        if (!isVideo && !isAudio) return@forEach
                        val uri = child.uri
                        out.add(
                            LocalMediaItem(
                                id = uri.hashCode().toLong(),
                                uri = uri,
                                title = name.substringBeforeLast('.').ifBlank { name },
                                artist = "",
                                album = dir.name.orEmpty(),
                                durationMs = 0L,
                                isVideo = isVideo,
                            ),
                        )
                    }
                }
            }
        }
        walk(root, 0)
        return out.sortedWith(compareBy(String.CASE_INSENSITIVE_ORDER) { it.title })
    }

    fun setLocalSearchQuery(q: String) {
        prefs.edit().putString(PREF_HOME_SEARCH, q).apply()
        _state.update { it.copy(localSearchQuery = q) }
    }

    fun setHomeAzLetter(letter: Char?) {
        val normalized = letter?.let { ch ->
            when {
                ch in 'A'..'Z' -> ch
                ch in 'a'..'z' -> ch.uppercaseChar()
                else -> '#'
            }
        }
        if (_state.value.homeAzLetter == normalized) return
        prefs.edit().apply {
            if (normalized == null) remove(PREF_HOME_AZ)
            else putString(PREF_HOME_AZ, normalized.toString())
        }.apply()
        _state.update { it.copy(homeAzLetter = normalized) }
    }

    fun setAudioFacet(facet: String) {
        val f = if (facet in AUDIO_FACETS) facet else "tracks"
        prefs.edit().putString(PREF_AUDIO_FACET, f).apply()
        _state.update { it.copy(audioFacet = f) }
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
        playLocalQueue(queue, start.coerceIn(0, queue.lastIndex))
    }

    /** Play every on-device audio track for an artist (Artists facet). */
    fun playArtist(artistKey: String) {
        val key = artistKey.ifBlank { UNKNOWN_ARTIST }
        val queue = _state.value.localItems
            .filter { !it.isVideo && artistKeyOf(it) == key }
            .sortedWith(
                compareBy(
                    { it.album.ifBlank { UNKNOWN_ALBUM }.lowercase() },
                    { it.title.lowercase() },
                ),
            )
        if (queue.isEmpty()) return
        playLocalQueue(queue, 0)
    }

    /** Play every on-device audio track for an album (Albums facet). */
    fun playAlbum(albumKey: String, artistKey: String) {
        val alb = albumKey.ifBlank { UNKNOWN_ALBUM }
        val art = artistKey.ifBlank { UNKNOWN_ARTIST }
        val queue = _state.value.localItems
            .filter {
                !it.isVideo && albumKeyOf(it) == alb && artistKeyOf(it) == art
            }
            .sortedWith(compareBy(String.CASE_INSENSITIVE_ORDER) { it.title })
        if (queue.isEmpty()) return
        playLocalQueue(queue, 0)
    }

    private fun playLocalQueue(queue: List<LocalMediaItem>, startIndex: Int) {
        if (queue.isEmpty()) return
        val idx = startIndex.coerceIn(0, queue.lastIndex)
        val current = queue[idx]
        val resumeMs = resumeStore.resumePositionMs(current.uri.toString(), current.durationMs)
        withPlayer { p ->
            p.setMediaItems(
                queue.map { mediaItemFromLocal(it) },
                idx,
                resumeMs,
            )
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
                idx,
                resumeMs,
            )
        }
        _state.update {
            it.copy(
                localTitle = current.title,
                localArtist = current.artist,
                localAlbum = current.album,
                localQueueIndex = idx,
                localQueueSize = queue.size,
                localIsVideo = current.isVideo,
                localPlaying = true,
                activeOutput = "This device",
                tab = AppTab.Local,
                connectOpen = false,
                resumeHint = if (resumeMs > 0L) "Resumed from ${fmt(resumeMs)}" else "",
            )
        }
    }

    private fun sFilterIsAll(): Boolean = _state.value.localFilter == "all"

    private fun artistKeyOf(item: LocalMediaItem): String =
        item.artist.trim().ifBlank { UNKNOWN_ARTIST }

    private fun albumKeyOf(item: LocalMediaItem): String =
        item.album.trim().ifBlank { UNKNOWN_ALBUM }

    fun playUri(uri: Uri, title: String = uri.lastPathSegment ?: "Media", isVideo: Boolean = true) {
        val match = _state.value.localItems.find { it.uri == uri }
        val resumeMs = resumeStore.resumePositionMs(uri.toString(), match?.durationMs ?: 0L)
        withPlayer { p ->
            p.setMediaItems(listOf(mediaItem(uri, title, isVideo = isVideo)), 0, resumeMs)
            p.prepare()
            p.play()
            queueStore.save(uri.toString(), title, resumeMs, isVideo)
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
                resumeHint = if (resumeMs > 0L) "Resumed from ${fmt(resumeMs)}" else "",
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
        clearedQueueUndo = null
        _state.update {
            it.copy(
                localPlaying = false,
                localTitle = "(nothing loaded)",
                localArtist = "",
                localAlbum = "",
                localQueueIndex = 0,
                localQueueSize = 0,
                localQueue = emptyList(),
                queueClearArmed = false,
                queueUndoAvailable = false,
            )
        }
    }

    /**
     * Two-step clear for Up next: first tap arms confirm; second clears and
     * keeps an undo snapshot for a few seconds.
     */
    fun requestClearLocalQueue() {
        val p = player
        if (p == null || p.mediaItemCount == 0) {
            _state.update {
                it.copy(statusToast = "Queue is empty", queueClearArmed = false)
            }
            clearStatusToastLater()
            return
        }
        if (!_state.value.queueClearArmed) {
            _state.update {
                it.copy(
                    queueClearArmed = true,
                    statusToast = "Tap Clear again to confirm",
                )
            }
            clearStatusToastLater()
            viewModelScope.launch {
                delay(4_000L)
                _state.update { s ->
                    if (s.queueClearArmed) s.copy(queueClearArmed = false) else s
                }
            }
            return
        }
        commitClearLocalQueue()
    }

    fun cancelClearLocalQueue() {
        _state.update {
            it.copy(queueClearArmed = false, statusToast = "Clear cancelled")
        }
        clearStatusToastLater()
    }

    private fun commitClearLocalQueue() {
        val p = player ?: return
        if (p.mediaItemCount == 0) return
        val snap = queueSnapshotFromPlayer(p)
        clearedQueueUndo = snap
        removedItemUndo = null
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
                queueClearArmed = false,
                queueUndoAvailable = true,
                queueItemUndoAvailable = false,
                statusToast = "Queue cleared · Undo available",
            )
        }
        clearStatusToastLater(6_000L)
        viewModelScope.launch {
            delay(8_000L)
            if (clearedQueueUndo === snap) {
                clearedQueueUndo = null
                _state.update { it.copy(queueUndoAvailable = false) }
            }
        }
    }

    fun undoClearLocalQueue() {
        val snap = clearedQueueUndo ?: run {
            _state.update { it.copy(statusToast = "Nothing to undo", queueUndoAvailable = false) }
            clearStatusToastLater()
            return
        }
        clearedQueueUndo = null
        restoreQueueSnapshot(snap)
        _state.update {
            it.copy(
                queueUndoAvailable = false,
                queueItemUndoAvailable = false,
                queueClearArmed = false,
                statusToast = "Queue restored",
            )
        }
        clearStatusToastLater()
    }

    /** Undo either a full clear or the last single-row remove, whichever is active. */
    fun undoLastQueueChange() {
        when {
            removedItemUndo != null -> undoRemoveQueueItem()
            clearedQueueUndo != null -> undoClearLocalQueue()
            else -> {
                _state.update {
                    it.copy(
                        statusToast = "Nothing to undo",
                        queueUndoAvailable = false,
                        queueItemUndoAvailable = false,
                    )
                }
                clearStatusToastLater()
            }
        }
    }

    private var clearedQueueUndo: PlaybackQueueStore.Snapshot? = null

    private data class RemovedQueueItem(
        val index: Int,
        val entry: PlaybackQueueStore.Entry,
        val wasCurrent: Boolean,
        val positionMs: Long,
    )

    private var removedItemUndo: RemovedQueueItem? = null

    private fun queueSnapshotFromPlayer(p: Player): PlaybackQueueStore.Snapshot {
        val entries = buildList {
            for (i in 0 until p.mediaItemCount) {
                val item = p.getMediaItemAt(i)
                val uri = item.localConfiguration?.uri?.toString()
                    ?: item.requestMetadata.mediaUri?.toString()
                    ?: continue
                val md = item.mediaMetadata
                add(
                    PlaybackQueueStore.Entry(
                        uri = uri,
                        title = md.title?.toString()
                            ?: Uri.parse(uri).lastPathSegment
                            ?: "Media",
                        artist = md.artist?.toString().orEmpty(),
                        album = md.albumTitle?.toString().orEmpty(),
                        isVideo = md.mediaType == MediaMetadata.MEDIA_TYPE_VIDEO
                            || md.mediaType == MediaMetadata.MEDIA_TYPE_MOVIE,
                    ),
                )
            }
        }
        val index = p.currentMediaItemIndex.coerceIn(0, (entries.size - 1).coerceAtLeast(0))
        return PlaybackQueueStore.Snapshot(
            entries = entries,
            index = index,
            positionMs = p.currentPosition.coerceAtLeast(0L),
        )
    }

    private fun restoreQueueSnapshot(snap: PlaybackQueueStore.Snapshot) {
        if (snap.entries.isEmpty()) return
        val items = snap.entries.map {
            mediaItem(
                Uri.parse(it.uri),
                it.title,
                it.artist,
                it.album,
                it.isVideo,
            )
        }
        val idx = snap.index.coerceIn(0, items.lastIndex)
        withPlayer { p ->
            p.setMediaItems(items, idx, snap.positionMs)
            p.prepare()
            p.play()
            queueStore.saveQueue(snap.entries, idx, snap.positionMs)
        }
        val cur = snap.entries[idx]
        _state.update {
            it.copy(
                localTitle = cur.title,
                localArtist = cur.artist,
                localAlbum = cur.album,
                localIsVideo = cur.isVideo,
                localQueueIndex = idx,
                localQueueSize = snap.entries.size,
                localPlaying = true,
                activeOutput = "This device",
                tab = AppTab.Local,
            )
        }
        player?.let { syncUiFromPlayer(it) }
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

    /** Gesture scrubber / tap-seek on Now Playing (local Media3 only). */
    fun seekLocal(positionMs: Long) {
        withPlayer { p ->
            val dur = p.duration.coerceAtLeast(0L).let { if (it < 0) 0L else it }
            val target = if (dur > 0L) positionMs.coerceIn(0L, dur) else positionMs.coerceAtLeast(0L)
            p.seekTo(target)
            _state.update {
                it.copy(
                    localPositionMs = target,
                    localDurationMs = dur,
                    localPositionLabel = "${fmt(target)} / ${fmt(dur)}",
                )
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

    fun setLocalRepeatMode(mode: Int) {
        val next = normalizeRepeatMode(mode)
        prefs.edit().putInt(PREF_REPEAT, next).apply()
        _state.update { it.copy(localRepeatMode = next) }
        withPlayer { p -> p.repeatMode = next }
    }

    /** Long-press: pin / clear preferred repeat mode (restored on cold start). */
    fun setPreferredRepeatMode(mode: Int) {
        val next = normalizeRepeatMode(mode)
        val current = loadPreferredRepeatMode()
        if (current != null && current == next) {
            prefs.edit().remove(PREF_REPEAT_PREFERRED).apply()
            _state.update {
                it.copy(
                    localRepeatPreferred = -1,
                    statusToast = "Preferred repeat cleared",
                )
            }
            clearStatusToastLater()
            return
        }
        prefs.edit().putInt(PREF_REPEAT_PREFERRED, next).apply()
        setLocalRepeatMode(next)
        _state.update {
            it.copy(
                localRepeatPreferred = next,
                statusToast = "Preferred · ${repeatLabel(next)}",
            )
        }
        clearStatusToastLater()
    }

    fun pinCurrentRepeatMode() {
        setPreferredRepeatMode(_state.value.localRepeatMode)
    }

    private fun loadBootRepeatMode(): Int =
        loadPreferredRepeatMode() ?: prefs.getInt(PREF_REPEAT, Player.REPEAT_MODE_OFF)
            .let { normalizeRepeatMode(it) }

    private fun loadPreferredRepeatMode(): Int? {
        if (!prefs.contains(PREF_REPEAT_PREFERRED)) return null
        return normalizeRepeatMode(prefs.getInt(PREF_REPEAT_PREFERRED, Player.REPEAT_MODE_OFF))
    }

    private fun normalizeRepeatMode(mode: Int): Int = when (mode) {
        Player.REPEAT_MODE_ONE, Player.REPEAT_MODE_ALL -> mode
        else -> Player.REPEAT_MODE_OFF
    }

    private fun repeatLabel(mode: Int): String = when (normalizeRepeatMode(mode)) {
        Player.REPEAT_MODE_ONE -> "Repeat one"
        Player.REPEAT_MODE_ALL -> "Repeat all"
        else -> "Repeat off"
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

    fun setLocalShuffle(enabled: Boolean) {
        prefs.edit().putBoolean(PREF_SHUFFLE, enabled).apply()
        _state.update { it.copy(localShuffle = enabled) }
        withPlayer { p ->
            p.shuffleModeEnabled = enabled
            syncUiFromPlayer(p)
        }
    }

    /**
     * Long-press: pin / clear preferred shuffle-on.
     * When pinned, cold start enables shuffle.
     */
    fun setPreferredShuffleOn() {
        val pinned = prefs.getBoolean(PREF_SHUFFLE_PREFERRED, false)
        if (pinned) {
            prefs.edit().putBoolean(PREF_SHUFFLE_PREFERRED, false).apply()
            _state.update {
                it.copy(
                    localShufflePreferred = false,
                    statusToast = "Preferred shuffle cleared",
                )
            }
            clearStatusToastLater()
            return
        }
        prefs.edit().putBoolean(PREF_SHUFFLE_PREFERRED, true).apply()
        setLocalShuffle(true)
        _state.update {
            it.copy(
                localShufflePreferred = true,
                statusToast = "Preferred · Shuffle on",
            )
        }
        clearStatusToastLater()
    }

    private fun loadBootShuffle(): Boolean =
        if (prefs.getBoolean(PREF_SHUFFLE_PREFERRED, false)) {
            true
        } else {
            prefs.getBoolean(PREF_SHUFFLE, false)
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
            val item = p.getMediaItemAt(index)
            val uri = item.localConfiguration?.uri?.toString()
                ?: item.requestMetadata.mediaUri?.toString()
            if (uri.isNullOrBlank()) {
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
                return@withPlayer
            }
            val md = item.mediaMetadata
            val entry = PlaybackQueueStore.Entry(
                uri = uri,
                title = md.title?.toString()
                    ?: Uri.parse(uri).lastPathSegment
                    ?: "Media",
                artist = md.artist?.toString().orEmpty(),
                album = md.albumTitle?.toString().orEmpty(),
                isVideo = md.mediaType == MediaMetadata.MEDIA_TYPE_VIDEO
                    || md.mediaType == MediaMetadata.MEDIA_TYPE_MOVIE,
            )
            val wasCurrent = index == p.currentMediaItemIndex
            val positionMs = if (wasCurrent) p.currentPosition.coerceAtLeast(0L) else 0L
            val undo = RemovedQueueItem(index, entry, wasCurrent, positionMs)
            removedItemUndo = undo
            clearedQueueUndo = null
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
                        queueUndoAvailable = false,
                        queueItemUndoAvailable = true,
                        queueClearArmed = false,
                        statusToast = "Removed “${entry.title}” · Undo",
                    )
                }
            } else {
                queueStore.saveFromPlayer(p)
                syncUiFromPlayer(p)
                _state.update {
                    it.copy(
                        queueUndoAvailable = false,
                        queueItemUndoAvailable = true,
                        queueClearArmed = false,
                        statusToast = "Removed “${entry.title}” · Undo",
                    )
                }
            }
            clearStatusToastLater(6_000L)
            viewModelScope.launch {
                delay(8_000L)
                if (removedItemUndo === undo) {
                    removedItemUndo = null
                    _state.update { s ->
                        if (s.queueItemUndoAvailable) s.copy(queueItemUndoAvailable = false) else s
                    }
                }
            }
        }
    }

    fun undoRemoveQueueItem() {
        val rem = removedItemUndo ?: run {
            _state.update {
                it.copy(statusToast = "Nothing to undo", queueItemUndoAvailable = false)
            }
            clearStatusToastLater()
            return
        }
        removedItemUndo = null
        val e = rem.entry
        val media = mediaItem(Uri.parse(e.uri), e.title, e.artist, e.album, e.isVideo)
        withPlayer { p ->
            if (p.mediaItemCount == 0) {
                p.setMediaItems(listOf(media), 0, rem.positionMs)
                p.prepare()
                if (rem.wasCurrent) p.play()
                queueStore.saveQueue(listOf(e), 0, rem.positionMs)
            } else {
                val idx = rem.index.coerceIn(0, p.mediaItemCount)
                p.addMediaItem(idx, media)
                if (rem.wasCurrent) {
                    p.seekTo(idx, rem.positionMs)
                    p.play()
                }
                queueStore.saveFromPlayer(p)
            }
            syncUiFromPlayer(p)
        }
        _state.update {
            it.copy(
                queueItemUndoAvailable = false,
                queueUndoAvailable = false,
                queueClearArmed = false,
                statusToast = "Restored “${e.title}”",
            )
        }
        clearStatusToastLater()
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
        val pin = AudioRoute.loadPin(ctx)
        val preferred = AudioRoute.loadPreferredId(ctx)
        _state.update {
            it.copy(
                audioDevices = devices,
                preferredAudioDeviceId = preferred,
                audioPinType = pin?.type ?: Int.MIN_VALUE,
                audioPinName = pin?.name.orEmpty(),
            )
        }
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

    /** Long-press: pin / clear sticky preferred sink (type + name; reconnect restores). */
    fun setPinnedAudioDevice(deviceId: Int) {
        if (deviceId == AudioRoute.DEFAULT_DEVICE_ID) return
        val app = getApplication<Application>()
        val device = _state.value.audioDevices.firstOrNull { it.id == deviceId } ?: run {
            refreshAudioDevices()
            _state.value.audioDevices.firstOrNull { it.id == deviceId }
        } ?: return
        val current = AudioRoute.loadPin(app)
        val next = AudioRoute.pinForDevice(device)
        if (current != null && current.matches(device)) {
            AudioRoute.clearPin(app)
            _state.update {
                it.copy(
                    audioPinType = Int.MIN_VALUE,
                    audioPinName = "",
                    statusToast = "Preferred sink cleared",
                )
            }
            clearStatusToastLater()
            return
        }
        AudioRoute.savePin(app, next)
        setPreferredAudioDevice(deviceId)
        _state.update {
            it.copy(
                audioPinType = next.type,
                audioPinName = next.name,
                statusToast = "Preferred · ${device.name}",
            )
        }
        clearStatusToastLater()
    }

    fun setEqPreset(preset: String) {
        val id = EqualizerControl.normalize(preset)
        val app = getApplication<Application>()
        val bands = when (id) {
            EqualizerControl.PRESET_CUSTOM -> EqualizerControl.loadBandsDb(app)
            EqualizerControl.PRESET_OFF, EqualizerControl.PRESET_FLAT -> EqualizerControl.zeroBands()
            else -> EqualizerControl.bandsForPreset(id)
        }
        if (id != EqualizerControl.PRESET_CUSTOM && id != EqualizerControl.PRESET_OFF) {
            EqualizerControl.saveBandsDb(app, bands)
        }
        EqualizerControl.savePreset(app, id)
        _state.update {
            it.copy(
                eqPreset = id,
                eqBandsDb = bands.toList(),
            )
        }
        val controller = player as? MediaController ?: return
        val args = Bundle().apply { putString(EqualizerControl.EXTRA_PRESET, id) }
        try {
            controller.sendCustomCommand(EqualizerControl.CMD_SET, args)
        } catch (e: Exception) {
            Log.w(TAG, "SET_EQ_PRESET failed", e)
        }
    }

    fun openEqSheet(open: Boolean) {
        _state.update { it.copy(eqSheetOpen = open) }
    }

    fun setEqBandDb(index: Int, valueDb: Float) {
        if (index !in 0 until EqualizerControl.BAND_COUNT) return
        val current = eqBandsArray()
        val snap = _state.value.eqSnapBands
        val next = if (snap) {
            EqualizerControl.withSnap(current, index, valueDb)
        } else {
            current.copyOf().also { it[index] = EqualizerControl.clampDb(valueDb) }
        }
        pushEqCustom(next, _state.value.eqPreampDb, snap)
    }

    fun setEqPreampDb(db: Float) {
        pushEqCustom(eqBandsArray(), db, _state.value.eqSnapBands)
    }

    fun setEqSnapBands(snap: Boolean) {
        val app = getApplication<Application>()
        EqualizerControl.saveSnap(app, snap)
        _state.update { it.copy(eqSnapBands = snap) }
        if (_state.value.eqPreset != EqualizerControl.PRESET_OFF) {
            pushEqCustom(eqBandsArray(), _state.value.eqPreampDb, snap)
        }
    }

    private fun eqBandsArray(): FloatArray =
        FloatArray(EqualizerControl.BAND_COUNT) { i ->
            _state.value.eqBandsDb.getOrElse(i) { 0f }
        }

    fun resetEqBands() {
        pushEqCustom(EqualizerControl.zeroBands(), 0f, _state.value.eqSnapBands)
    }

    private fun pushEqCustom(bands: FloatArray, preampDb: Float, snap: Boolean) {
        val app = getApplication<Application>()
        val pre = EqualizerControl.clampPreamp(preampDb)
        val safe = FloatArray(EqualizerControl.BAND_COUNT) { i ->
            EqualizerControl.clampDb(bands.getOrElse(i) { 0f })
        }
        EqualizerControl.savePreset(app, EqualizerControl.PRESET_CUSTOM)
        EqualizerControl.saveBandsDb(app, safe)
        EqualizerControl.savePreampDb(app, pre)
        EqualizerControl.saveSnap(app, snap)
        _state.update {
            it.copy(
                eqPreset = EqualizerControl.PRESET_CUSTOM,
                eqBandsDb = safe.toList(),
                eqPreampDb = pre,
                eqSnapBands = snap,
            )
        }
        val controller = player as? MediaController ?: return
        val args = Bundle().apply {
            putFloatArray(EqualizerControl.EXTRA_BANDS, safe)
            putFloat(EqualizerControl.EXTRA_PREAMP, pre)
            putBoolean(EqualizerControl.EXTRA_SNAP, snap)
        }
        try {
            controller.sendCustomCommand(EqualizerControl.CMD_SET_CUSTOM, args)
        } catch (e: Exception) {
            Log.w(TAG, "SET_EQ_CUSTOM failed", e)
        }
    }

    /** Long-press: pin / clear preferred EQ (restored on cold start / audio reapply). */
    fun setPreferredEqPreset(preset: String) {
        val id = EqualizerControl.normalize(preset)
        val app = getApplication<Application>()
        val current = EqualizerControl.loadPreferred(app)
        if (current == id) {
            EqualizerControl.clearPreferred(app)
            _state.update {
                it.copy(
                    eqPreferredId = "",
                    statusToast = "Preferred EQ cleared",
                )
            }
            clearStatusToastLater()
            return
        }
        EqualizerControl.savePreferred(app, id)
        setEqPreset(id)
        _state.update {
            it.copy(
                eqPreferredId = id,
                statusToast = "Preferred EQ · ${EqualizerControl.label(id)}",
            )
        }
        clearStatusToastLater()
    }

    /** Quest panel / foldable / multi-window: record layout flags; playback stays in the service. */
    fun onWindowLayoutChanged(multiWindow: Boolean, orientation: Int) {
        _state.update {
            it.copy(
                multiWindow = multiWindow,
                // Orientation kept for diagnostics; Compose uses BoxWithConstraints for layout.
            )
        }
        Log.i(TAG, "window layout multiWindow=$multiWindow orientation=$orientation")
    }

    fun updateFoldLayout(foldSeparating: Boolean) {
        if (_state.value.foldSeparating == foldSeparating) return
        _state.update { it.copy(foldSeparating = foldSeparating) }
    }

    /** Quest panel refocus / activity resume: refresh sinks and re-bind audio chain. */
    fun reapplyLocalAudio() {
        refreshAudioDevices()
        val pin = AudioRoute.loadPin(getApplication())
        _state.update {
            it.copy(
                localVolume = LocalVolume.loadPercent(getApplication()),
                localMuted = LocalVolume.loadMuted(getApplication()),
                preferredAudioDeviceId = AudioRoute.loadPreferredId(getApplication()),
                audioPinType = pin?.type ?: Int.MIN_VALUE,
                audioPinName = pin?.name.orEmpty(),
                eqPreset = EqualizerControl.loadBootPreset(getApplication()),
                eqPreferredId = EqualizerControl.loadPreferred(getApplication()).orEmpty(),
                playbackSpeed = PlaybackSpeed.loadBoot(getApplication()),
                playbackSpeedPreferred = PlaybackSpeed.loadPreferred(getApplication()) ?: Float.NaN,
                fadeMs = CrossfadeControl.loadBootFadeMs(getApplication()),
                fadeMsPreferred = CrossfadeControl.loadPreferredFadeMs(getApplication()) ?: -1L,
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
                val uri = item.localConfiguration?.uri?.toString()
                    ?: item.requestMetadata.mediaUri?.toString()
                    ?: ""
                add(
                    QueueRow(
                        index = i,
                        title = title,
                        artist = artist,
                        isCurrent = i == current,
                        uri = uri,
                    ),
                )
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
                    QueueRow(i, e.title, e.artist, i == snap.index, e.uri)
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
                localPositionMs = pos,
                localDurationMs = dur,
                sleepEndEpochMs = sleepEnd,
                sleepRemainingLabel = SleepTimer.remainingLabel(sleepEnd),
            )
        }
        refreshLyricsFor(currentPlayerUri(p), pos)
        // Auto-save resume bookmark ~every 5s while playing (desktop companion parity).
        if (p.isPlaying && pos >= 1_500L && System.currentTimeMillis() / 5_000L != lastBookmarkAutosaveBucket) {
            lastBookmarkAutosaveBucket = System.currentTimeMillis() / 5_000L
            autosaveBookmark(p)
            autosaveTrackResume(p, pos, dur)
        }
        // Finished (or near end): drop silent resume so next open starts at 0.
        if (dur > 0L && pos + 12_000L >= dur) {
            currentPlayerUri(p)?.let { resumeStore.clear(it) }
        }
        // Scrobble-free history: one count per media URI after ~3s of play.
        if (p.isPlaying && pos >= 3_000L) {
            maybeRecordHistory(p)
        }
    }

    private var lastBookmarkAutosaveBucket = -1L
    private var lastHistoryRecordedUri: String? = null
    private var lastLyricsUri: String? = null
    private var loadedLyrics: LyricsLoader.Lyrics? = null

    private fun currentPlayerUri(p: Player): String? {
        val item = p.currentMediaItem ?: return null
        return item.localConfiguration?.uri?.toString()
            ?: item.requestMetadata.mediaUri?.toString()
    }

    private fun refreshLyricsFor(uri: String?, positionMs: Long) {
        if (uri.isNullOrBlank()) {
            lastLyricsUri = null
            loadedLyrics = null
            _state.update {
                it.copy(
                    lyricsSource = "",
                    lyricsTimed = false,
                    lyricsLines = emptyList(),
                    lyricsActiveIndex = -1,
                )
            }
            return
        }
        if (uri != lastLyricsUri) {
            lastLyricsUri = uri
            loadedLyrics = try {
                LyricsLoader.load(getApplication(), Uri.parse(uri))
            } catch (_: Exception) {
                null
            }
        }
        val lyr = loadedLyrics
        if (lyr == null) {
            _state.update {
                it.copy(
                    lyricsSource = "",
                    lyricsTimed = false,
                    lyricsLines = emptyList(),
                    lyricsActiveIndex = -1,
                )
            }
            return
        }
        val idx = lyr.activeIndex(positionMs)
        _state.update {
            it.copy(
                lyricsSource = lyr.sourceLabel,
                lyricsTimed = lyr.timed,
                lyricsLines = lyr.lines.map { line -> line.text },
                lyricsActiveIndex = idx,
            )
        }
    }

    private fun maybeRecordHistory(p: Player) {
        val uri = currentPlayerUri(p) ?: return
        if (uri == lastHistoryRecordedUri) return
        lastHistoryRecordedUri = uri
        val md = p.currentMediaItem?.mediaMetadata
        historyStore.recordPlay(
            uri = uri,
            title = md?.title?.toString()
                ?: _state.value.localTitle.takeIf { it != "(nothing loaded)" }
                ?: Uri.parse(uri).lastPathSegment
                ?: "Media",
            artist = md?.artist?.toString() ?: _state.value.localArtist,
            album = md?.albumTitle?.toString() ?: _state.value.localAlbum,
            isVideo = _state.value.localIsVideo,
        )
        refreshHistoryFacets()
    }

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

    private fun autosaveTrackResume(p: Player, pos: Long, dur: Long) {
        val uri = currentPlayerUri(p) ?: return
        resumeStore.save(uri, pos, dur)
    }

    fun clearTrackResume() {
        val uri = player?.let { currentPlayerUri(it) } ?: return
        resumeStore.clear(uri)
        _state.update { it.copy(resumeHint = "") }
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

    /** Long-press: pin / clear preferred sleep duration (does not arm by itself). */
    fun setPreferredSleepMinutes(minutes: Int) {
        if (minutes <= 0) return
        val m = SleepTimer.normalizeMinutes(minutes)
        val app = getApplication<Application>()
        val current = SleepTimer.loadPreferredMinutes(app)
        if (current != null && current == m) {
            SleepTimer.clearPreferredMinutes(app)
            _state.update {
                it.copy(
                    sleepPreferredMinutes = 0,
                    statusToast = "Preferred sleep cleared",
                )
            }
            clearStatusToastLater()
            return
        }
        SleepTimer.savePreferredMinutes(app, m)
        setSleepTimerMinutes(m)
        _state.update {
            it.copy(
                sleepPreferredMinutes = m,
                statusToast = "Preferred sleep · ${m}m",
            )
        }
        clearStatusToastLater()
    }

    /** One-tap re-arm using the pinned preferred duration. */
    fun startPreferredSleepTimer() {
        val m = SleepTimer.loadPreferredMinutes(getApplication()) ?: return
        setSleepTimerMinutes(m)
        _state.update { it.copy(statusToast = "Sleep ${m}m") }
        clearStatusToastLater()
    }

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

    fun playHistory(entry: PlayHistoryStore.Entry) {
        val match = _state.value.localItems.find { it.uri.toString() == entry.uri }
        if (match != null) {
            playLocal(match)
            return
        }
        playUri(Uri.parse(entry.uri), entry.title, entry.isVideo)
        _state.update {
            it.copy(localArtist = entry.artist, localAlbum = entry.album)
        }
    }

    fun clearPlayHistory() {
        historyStore.clear()
        lastHistoryRecordedUri = null
        refreshHistoryFacets()
    }

    fun setDlnaEnabled(enabled: Boolean) {
        DlnaCastControl.saveEnabled(getApplication(), enabled)
        _state.update {
            it.copy(
                dlnaEnabled = enabled,
                dlnaMessage = if (enabled) {
                    "DLNA on — scan for renderers on this Wi‑Fi (no Google Cast)"
                } else {
                    ""
                },
                dlnaRenderers = if (enabled) it.dlnaRenderers else emptyList(),
            )
        }
        if (enabled) {
            DlnaCastControl.ensureInit(getApplication())
        } else {
            viewModelScope.launch {
                try {
                    DlnaCastControl.stop()
                } catch (_: Exception) {
                }
                DlnaCastControl.cleanup()
            }
        }
    }

    fun scanDlnaRenderers() {
        if (!_state.value.dlnaEnabled) {
            _state.update { it.copy(dlnaMessage = "Enable DLNA cast first") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(dlnaBusy = true, dlnaMessage = "Scanning LAN for MediaRenderers…") }
            try {
                val list = DlnaCastControl.search(getApplication())
                val defaultId = DlnaCastControl.loadDefaultId(getApplication())
                _state.update {
                    val pick = when {
                        defaultId.isNotBlank() && list.any { r -> r.id == defaultId } -> defaultId
                        it.dlnaSelectedId.isNotBlank() && list.any { r -> r.id == it.dlnaSelectedId } ->
                            it.dlnaSelectedId
                        else -> list.firstOrNull()?.id.orEmpty()
                    }
                    it.copy(
                        dlnaBusy = false,
                        dlnaRenderers = list,
                        dlnaDefaultId = defaultId,
                        dlnaSelectedId = pick,
                        dlnaMessage = if (list.isEmpty()) {
                            "No DLNA renderers found on this network"
                        } else {
                            buildString {
                                append("Found ${list.size} renderer(s)")
                                if (defaultId.isNotBlank() && pick == defaultId) {
                                    append(" · default selected")
                                }
                            }
                        },
                    )
                }
            } catch (e: Exception) {
                _state.update {
                    it.copy(dlnaBusy = false, dlnaMessage = e.message ?: e.toString())
                }
            }
        }
    }

    fun selectDlnaRenderer(id: String) {
        _state.update { it.copy(dlnaSelectedId = id) }
    }

    /** Long-press: pin as default renderer (toggle off if already default). */
    fun setDlnaDefaultRenderer(id: String) {
        if (id.isBlank()) return
        val app = getApplication<Application>()
        val current = DlnaCastControl.loadDefaultId(app)
        if (current == id) {
            DlnaCastControl.clearDefaultId(app)
            _state.update {
                it.copy(
                    dlnaDefaultId = "",
                    statusToast = "DLNA default cleared",
                    dlnaMessage = "No default renderer",
                )
            }
            clearStatusToastLater()
            return
        }
        DlnaCastControl.saveDefaultId(app, id)
        val name = _state.value.dlnaRenderers.find { it.id == id }?.name ?: "renderer"
        _state.update {
            it.copy(
                dlnaDefaultId = id,
                dlnaSelectedId = id,
                statusToast = "Default DLNA · $name",
                dlnaMessage = "Default · $name",
            )
        }
        clearStatusToastLater()
    }

    fun castNowPlayingToDlna() {
        if (!_state.value.dlnaEnabled) return
        val deviceId = _state.value.dlnaSelectedId
        if (deviceId.isBlank()) {
            _state.update { it.copy(dlnaMessage = "Select a renderer first") }
            return
        }
        val p = player
        val item = p?.currentMediaItem
        val uriStr = item?.localConfiguration?.uri?.toString()
            ?: item?.requestMetadata?.mediaUri?.toString()
        if (uriStr.isNullOrBlank()) {
            _state.update { it.copy(dlnaMessage = "Nothing loaded to cast") }
            return
        }
        val title = item?.mediaMetadata?.title?.toString()
            ?: _state.value.localTitle
        val mime = getApplication<Application>().contentResolver.getType(Uri.parse(uriStr)).orEmpty()
        viewModelScope.launch {
            _state.update { it.copy(dlnaBusy = true, dlnaMessage = "Casting…") }
            try {
                // Pause local playback so the TV is the audible sink.
                p?.pause()
                val msg = DlnaCastControl.castUri(
                    getApplication(),
                    deviceId,
                    Uri.parse(uriStr),
                    title,
                    mime,
                )
                _state.update {
                    it.copy(
                        dlnaBusy = false,
                        dlnaMessage = msg,
                        activeOutput = "DLNA · ${it.dlnaRenderers.find { r -> r.id == deviceId }?.name ?: "TV"}",
                    )
                }
            } catch (e: Exception) {
                _state.update {
                    it.copy(dlnaBusy = false, dlnaMessage = e.message ?: e.toString())
                }
            }
        }
    }

    fun dlnaPause() {
        viewModelScope.launch {
            try {
                DlnaCastControl.pause()
                _state.update { it.copy(dlnaMessage = "DLNA paused") }
            } catch (e: Exception) {
                _state.update { it.copy(dlnaMessage = e.message ?: e.toString()) }
            }
        }
    }

    fun dlnaPlay() {
        viewModelScope.launch {
            try {
                DlnaCastControl.play()
                _state.update { it.copy(dlnaMessage = "DLNA playing") }
            } catch (e: Exception) {
                _state.update { it.copy(dlnaMessage = e.message ?: e.toString()) }
            }
        }
    }

    fun dlnaStop() {
        viewModelScope.launch {
            try {
                DlnaCastControl.stop()
                _state.update {
                    it.copy(
                        dlnaMessage = "DLNA stopped",
                        activeOutput = "This device",
                    )
                }
            } catch (e: Exception) {
                _state.update { it.copy(dlnaMessage = e.message ?: e.toString()) }
            }
        }
    }

    /** Offline now-playing PNG card → system share sheet (no cloud). */
    fun shareNowPlayingCard(activityContext: android.content.Context) {
        val s = _state.value
        if (s.localTitle.isBlank() || s.localTitle == "(nothing loaded)") {
            _state.update { it.copy(error = "Nothing playing to share") }
            return
        }
        viewModelScope.launch {
            try {
                val p = player
                val uri = p?.currentMediaItem?.localConfiguration?.uri
                    ?: p?.currentMediaItem?.requestMetadata?.mediaUri
                val art = uri?.let { u ->
                    val match = s.localItems.find { it.uri == u }
                    match?.artworkContentUri() ?: u
                }
                val intent = withContext(Dispatchers.IO) {
                    NowPlayingShare.shareCard(
                        activityContext.applicationContext,
                        title = s.localTitle,
                        artist = s.localArtist,
                        album = s.localAlbum,
                        artworkUri = art,
                    )
                }
                activityContext.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            } catch (e: Exception) {
                _state.update { it.copy(error = e.message ?: e.toString()) }
            }
        }
    }

    fun openListsBrowse(id: String?) {
        _state.update { it.copy(listsBrowseId = id, localFilter = "lists") }
    }

    fun createLocalPlaylist() {
        val n = playlistStore.load().size + 1
        playlistStore.create("Playlist $n")
        refreshPlaylists()
    }

    fun openAddToList(item: LocalMediaItem) {
        _state.update {
            it.copy(
                addToListPending = item.toPlaylistTrack(),
                addToListExcludePlaylistId = null,
                statusToast = "Choose a list for “${item.title}”",
            )
        }
        clearStatusToastLater()
    }

    fun openAddToListFromHistory(entry: PlayHistoryStore.Entry) {
        openAddToListFromTrack(
            LocalPlaylistStore.Track(
                uri = entry.uri,
                title = entry.title,
                artist = entry.artist,
                album = entry.album,
                isVideo = entry.isVideo,
            ),
        )
    }

    fun openAddToListFromTrack(track: LocalPlaylistStore.Track, excludePlaylistId: String? = null) {
        if (track.uri.isBlank()) return
        _state.update {
            it.copy(
                addToListPending = track,
                addToListExcludePlaylistId = excludePlaylistId,
                statusToast = "Choose a list for “${track.title}”",
            )
        }
        clearStatusToastLater()
    }

    fun openAddToListFromQueueRow(row: QueueRow) {
        if (row.uri.isBlank()) {
            _state.update { it.copy(statusToast = "Queue item has no URI to save") }
            clearStatusToastLater()
            return
        }
        val fromLib = _state.value.localItems.find { it.uri.toString() == row.uri }
        openAddToListFromTrack(
            LocalPlaylistStore.Track(
                uri = row.uri,
                title = row.title,
                artist = row.artist,
                album = fromLib?.album.orEmpty(),
                isVideo = fromLib?.isVideo == true,
            ),
        )
    }

    fun openAddToListFromBookmark(bm: BookmarkStore.Bookmark) {
        if (bm.uri.isBlank()) {
            _state.update { it.copy(statusToast = "Bookmark has no URI to save") }
            clearStatusToastLater()
            return
        }
        val fromLib = _state.value.localItems.find { it.uri.toString() == bm.uri }
        openAddToListFromTrack(
            LocalPlaylistStore.Track(
                uri = bm.uri,
                title = bm.title,
                artist = fromLib?.artist.orEmpty(),
                album = fromLib?.album.orEmpty(),
                isVideo = bm.isVideo || fromLib?.isVideo == true,
            ),
        )
    }

    fun dismissAddToList() {
        _state.update { it.copy(addToListPending = null, addToListExcludePlaylistId = null) }
    }

    fun addPendingToPlaylist(playlistId: String) {
        val track = _state.value.addToListPending ?: return
        playlistStore.addTrack(playlistId, track)
        val name = playlistStore.load().find { it.id == playlistId }?.name ?: "list"
        refreshPlaylists()
        _state.update {
            it.copy(
                addToListPending = null,
                addToListExcludePlaylistId = null,
                statusToast = "Added “${track.title}” to $name",
            )
        }
        clearStatusToastLater()
    }

    fun createPlaylistAndAddPending() {
        val track = _state.value.addToListPending ?: return
        val n = playlistStore.load().size + 1
        val pl = playlistStore.createWithTracks("Playlist $n", listOf(track))
        refreshPlaylists()
        _state.update {
            it.copy(
                addToListPending = null,
                addToListExcludePlaylistId = null,
                localFilter = "lists",
                listsBrowseId = pl.id,
                statusToast = "Added “${track.title}” to ${pl.name}",
            )
        }
        clearStatusToastLater()
    }

    /** Export Up Next / current Media3 queue as offline M3U via system share. */
    fun exportQueueM3u(activityContext: android.content.Context) {
        viewModelScope.launch {
            try {
                val p = player
                val entries = buildList {
                    if (p == null || p.mediaItemCount <= 0) return@buildList
                    for (i in 0 until p.mediaItemCount) {
                        val item = p.getMediaItemAt(i)
                        val uri = item.localConfiguration?.uri
                            ?: item.requestMetadata.mediaUri
                            ?: continue
                        val md = item.mediaMetadata
                        val title = buildString {
                            val t = md.title?.toString().orEmpty()
                            val a = md.artist?.toString().orEmpty()
                            when {
                                t.isNotBlank() && a.isNotBlank() -> append(a).append(" - ").append(t)
                                t.isNotBlank() -> append(t)
                                else -> append(uri.lastPathSegment ?: "Track")
                            }
                        }
                        val durMs = md.durationMs ?: -1L
                        val durSec = if (durMs > 0L) (durMs / 1000L).toInt() else -1
                        add(M3uPlaylist.Entry(uri.toString(), title, durSec))
                    }
                }
                if (entries.isEmpty()) {
                    _state.update { it.copy(error = "Queue is empty — nothing to export") }
                    return@launch
                }
                val name = "Up next"
                val intent = withContext(Dispatchers.IO) {
                    val file = M3uPlaylist.writeCacheFile(activityContext.applicationContext, name, entries)
                    M3uPlaylist.shareIntent(activityContext.applicationContext, file, name)
                }
                activityContext.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            } catch (e: Exception) {
                _state.update { it.copy(error = e.message ?: e.toString()) }
            }
        }
    }

    /** Export a user playlist folder as offline M3U. */
    fun exportPlaylistM3u(activityContext: android.content.Context, playlistId: String) {
        viewModelScope.launch {
            try {
                val pl = playlistStore.load().find { it.id == playlistId }
                if (pl == null || pl.tracks.isEmpty()) {
                    _state.update { it.copy(error = "Playlist empty — nothing to export") }
                    return@launch
                }
                val entries = pl.tracks.map { t ->
                    val title = if (t.artist.isNotBlank()) "${t.artist} - ${t.title}" else t.title
                    M3uPlaylist.Entry(t.uri, title, -1)
                }
                val intent = withContext(Dispatchers.IO) {
                    val file = M3uPlaylist.writeCacheFile(
                        activityContext.applicationContext,
                        pl.name,
                        entries,
                    )
                    M3uPlaylist.shareIntent(activityContext.applicationContext, file, pl.name)
                }
                activityContext.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            } catch (e: Exception) {
                _state.update { it.copy(error = e.message ?: e.toString()) }
            }
        }
    }

    /** Import M3U/M3U8 from SAF into a new on-device playlist folder. */
    fun importM3u(uri: Uri) {
        viewModelScope.launch {
            try {
                val app = getApplication<Application>()
                val (name, entries) = withContext(Dispatchers.IO) {
                    app.contentResolver.openInputStream(uri)?.use { M3uPlaylist.parse(it) }
                        ?: error("Could not read M3U")
                }
                if (entries.isEmpty()) {
                    _state.update { it.copy(error = "M3U had no local tracks") }
                    return@launch
                }
                val tracks = M3uPlaylist.resolveToTracks(entries, _state.value.localItems)
                if (tracks.isEmpty()) {
                    _state.update {
                        it.copy(error = "No matching on-device tracks in M3U (${entries.size} lines)")
                    }
                    return@launch
                }
                val pl = playlistStore.createWithTracks(name, tracks)
                refreshPlaylists()
                _state.update {
                    it.copy(
                        localFilter = "lists",
                        listsBrowseId = pl.id,
                        error = "",
                        syncMessage = "Imported ${tracks.size} tracks → ${pl.name}",
                    )
                }
            } catch (e: Exception) {
                _state.update { it.copy(error = e.message ?: e.toString()) }
            }
        }
    }

    fun deleteLocalPlaylist(id: String) {
        playlistStore.delete(id)
        _state.update {
            it.copy(
                localPlaylists = playlistStore.load(),
                listsBrowseId = if (it.listsBrowseId == id) null else it.listsBrowseId,
            )
        }
    }

    fun addNowPlayingToPlaylist(id: String) {
        val p = player ?: return
        val uri = currentPlayerUri(p) ?: return
        val md = p.currentMediaItem?.mediaMetadata
        playlistStore.addTrack(
            id,
            LocalPlaylistStore.Track(
                uri = uri,
                title = md?.title?.toString()
                    ?: _state.value.localTitle.takeIf { it != "(nothing loaded)" }
                    ?: Uri.parse(uri).lastPathSegment
                    ?: "Track",
                artist = md?.artist?.toString() ?: _state.value.localArtist,
                album = md?.albumTitle?.toString() ?: _state.value.localAlbum,
                isVideo = _state.value.localIsVideo,
            ),
        )
        refreshPlaylists()
    }

    fun removeFromLocalPlaylist(playlistId: String, uri: String) {
        playlistStore.removeTrack(playlistId, uri)
        refreshPlaylists()
    }

    fun playSmartList(kind: String) {
        val queue = smartListTracks(kind)
        if (queue.isEmpty()) {
            _state.update { it.copy(error = "Smart list is empty") }
            return
        }
        playTrackQueue(queue, 0)
    }

    fun playLocalPlaylist(id: String, startIndex: Int = 0) {
        val pl = playlistStore.load().find { it.id == id } ?: return
        if (pl.tracks.isEmpty()) {
            _state.update { it.copy(error = "Playlist is empty — add the Now Playing track") }
            return
        }
        playTrackQueue(pl.tracks, startIndex.coerceIn(0, pl.tracks.lastIndex))
    }

    fun playListsBrowseTrack(uri: String) {
        val browse = _state.value.listsBrowseId ?: return
        when {
            browse.startsWith("smart:") -> {
                val q = smartListTracks(browse)
                val idx = q.indexOfFirst { it.uri == uri }.coerceAtLeast(0)
                playTrackQueue(q, idx)
            }
            else -> {
                val pl = _state.value.localPlaylists.find { it.id == browse } ?: return
                val idx = pl.tracks.indexOfFirst { it.uri == uri }.coerceAtLeast(0)
                playTrackQueue(pl.tracks, idx)
            }
        }
    }

    private fun smartListTracks(kind: String): List<LocalPlaylistStore.Track> {
        val s = _state.value
        return when (kind) {
            LocalPlaylistStore.SMART_NEW -> s.localItems.take(40).map { it.toPlaylistTrack() }
            LocalPlaylistStore.SMART_RECENT -> s.historyRecent.map {
                LocalPlaylistStore.Track(it.uri, it.title, it.artist, it.album, it.isVideo)
            }
            LocalPlaylistStore.SMART_TOP -> s.historyTop.map {
                LocalPlaylistStore.Track(it.uri, it.title, it.artist, it.album, it.isVideo)
            }
            LocalPlaylistStore.SMART_SHORT -> s.localItems
                .filter { !it.isVideo && it.durationMs in 1L..180_000L }
                .take(40)
                .map { it.toPlaylistTrack() }
            else -> emptyList()
        }
    }

    private fun LocalMediaItem.toPlaylistTrack() = LocalPlaylistStore.Track(
        uri = uri.toString(),
        title = title,
        artist = artist,
        album = album,
        isVideo = isVideo,
    )

    fun setCrossfadeEnabled(enabled: Boolean) {
        val skip = _state.value.skipSilence
        val fade = _state.value.fadeMs
        CrossfadeControl.save(getApplication(), enabled, skip, fade)
        _state.update {
            it.copy(
                crossfadeEnabled = enabled,
                statusToast = if (enabled) "Fade-in on" else "Fade-in off",
            )
        }
        sendCrossfadeCommand(enabled, skip, fade)
        clearStatusToastLater()
    }

    fun setSkipSilence(enabled: Boolean) {
        val cross = _state.value.crossfadeEnabled
        val fade = _state.value.fadeMs
        CrossfadeControl.save(getApplication(), cross, enabled, fade)
        _state.update {
            it.copy(
                skipSilence = enabled,
                statusToast = if (enabled) {
                    "Skip silence on — quiet gaps will be jumped"
                } else {
                    "Skip silence off"
                },
            )
        }
        sendCrossfadeCommand(cross, enabled, fade)
        clearStatusToastLater()
    }

    fun clearStatusToast() {
        _state.update { it.copy(statusToast = "") }
    }

    private fun clearStatusToastLater(afterMs: Long = 3_200L) {
        viewModelScope.launch {
            delay(afterMs)
            _state.update { s -> if (s.statusToast.isNotBlank()) s.copy(statusToast = "") else s }
        }
    }

    fun setFadeMs(ms: Long) {
        val fade = CrossfadeControl.normalizeFadeMs(ms)
        val cross = _state.value.crossfadeEnabled
        val skip = _state.value.skipSilence
        CrossfadeControl.save(getApplication(), cross, skip, fade)
        _state.update { it.copy(fadeMs = fade, crossfadeEnabled = true) }
        sendCrossfadeCommand(true, skip, fade)
    }

    /** Long-press: pin / clear preferred fade-in length. */
    fun setPreferredFadeMs(ms: Long) {
        val fade = CrossfadeControl.normalizeFadeMs(ms)
        val app = getApplication<Application>()
        val current = CrossfadeControl.loadPreferredFadeMs(app)
        if (current != null && current == fade) {
            CrossfadeControl.clearPreferredFadeMs(app)
            _state.update {
                it.copy(
                    fadeMsPreferred = -1L,
                    statusToast = "Preferred fade cleared",
                )
            }
            clearStatusToastLater()
            return
        }
        CrossfadeControl.savePreferredFadeMs(app, fade)
        setFadeMs(fade)
        _state.update {
            it.copy(
                fadeMsPreferred = fade,
                statusToast = "Preferred fade · ${CrossfadeControl.fadeLabel(fade)}",
            )
        }
        clearStatusToastLater()
    }

    fun setPlaybackSpeed(speed: Float) {
        val s = PlaybackSpeed.normalize(speed)
        PlaybackSpeed.save(getApplication(), s)
        _state.update {
            it.copy(
                playbackSpeed = s,
                statusToast = "Speed ${PlaybackSpeed.label(s)}",
            )
        }
        clearStatusToastLater()
        val controller = player as? MediaController ?: return
        val args = Bundle().apply { putFloat(PlaybackSpeed.EXTRA_SPEED, s) }
        try {
            controller.sendCustomCommand(PlaybackSpeed.CMD_SET, args)
        } catch (e: Exception) {
            Log.w(TAG, "SET_PLAYBACK_SPEED failed", e)
            player?.let { PlaybackSpeed.apply(it, s) }
        }
    }

    /** Long-press: pin / clear preferred playback speed. */
    fun setPreferredPlaybackSpeed(speed: Float) {
        val s = PlaybackSpeed.normalize(speed)
        val app = getApplication<Application>()
        val current = PlaybackSpeed.loadPreferred(app)
        if (current != null && PlaybackSpeed.isSame(current, s)) {
            PlaybackSpeed.clearPreferred(app)
            _state.update {
                it.copy(
                    playbackSpeedPreferred = Float.NaN,
                    statusToast = "Preferred speed cleared",
                )
            }
            clearStatusToastLater()
            return
        }
        PlaybackSpeed.savePreferred(app, s)
        setPlaybackSpeed(s)
        _state.update {
            it.copy(
                playbackSpeedPreferred = s,
                statusToast = "Preferred speed · ${PlaybackSpeed.label(s)}",
            )
        }
        clearStatusToastLater()
    }

    fun setThemeMode(mode: ThemeMode) {
        ThemePrefs.save(getApplication(), mode)
        _state.update { it.copy(themeMode = mode) }
    }

    /** Long-press: pin / clear preferred theme (restored on cold start). */
    fun setPreferredThemeMode(mode: ThemeMode) {
        val app = getApplication<Application>()
        val current = ThemePrefs.loadPreferred(app)
        if (current == mode) {
            ThemePrefs.clearPreferred(app)
            _state.update {
                it.copy(
                    themePreferred = null,
                    statusToast = "Preferred theme cleared",
                )
            }
            clearStatusToastLater()
            return
        }
        ThemePrefs.savePreferred(app, mode)
        setThemeMode(mode)
        _state.update {
            it.copy(
                themePreferred = mode,
                statusToast = "Preferred theme · ${mode.label()}",
            )
        }
        clearStatusToastLater()
    }

    fun cycleThemeMode() {
        val next = when (_state.value.themeMode) {
            ThemeMode.Dark -> ThemeMode.Light
            ThemeMode.Light -> ThemeMode.System
            ThemeMode.System -> ThemeMode.Dark
        }
        setThemeMode(next)
    }

    /** Settings strip: clear every preferred pin (Home filter, theme, transport, audio, EQ, speed, fade, sleep, DLNA). */
    fun clearAllPreferredPins() {
        val app = getApplication<Application>()
        prefs.edit()
            .remove(PREF_HOME_FILTER_PREFERRED)
            .remove(PREF_REPEAT_PREFERRED)
            .putBoolean(PREF_SHUFFLE_PREFERRED, false)
            .apply()
        ThemePrefs.clearPreferred(app)
        EqualizerControl.clearPreferred(app)
        PlaybackSpeed.clearPreferred(app)
        CrossfadeControl.clearPreferredFadeMs(app)
        SleepTimer.clearPreferredMinutes(app)
        AudioRoute.clearPin(app)
        DlnaCastControl.clearDefaultId(app)
        _state.update {
            it.copy(
                localFilterPreferred = "",
                localRepeatPreferred = -1,
                localShufflePreferred = false,
                themePreferred = null,
                eqPreferredId = "",
                playbackSpeedPreferred = Float.NaN,
                fadeMsPreferred = -1L,
                sleepPreferredMinutes = 0,
                audioPinType = Int.MIN_VALUE,
                audioPinName = "",
                dlnaDefaultId = "",
                statusToast = "Preferred pins cleared",
                dlnaMessage = if (it.dlnaEnabled) "No default renderer" else it.dlnaMessage,
            )
        }
        clearStatusToastLater()
    }

    private fun sendCrossfadeCommand(crossfade: Boolean, skipSilence: Boolean, fadeMs: Long) {
        val controller = player as? MediaController ?: return
        val args = Bundle().apply {
            putBoolean(CrossfadeControl.EXTRA_CROSSFADE, crossfade)
            putBoolean(CrossfadeControl.EXTRA_SKIP_SILENCE, skipSilence)
            putLong(CrossfadeControl.EXTRA_FADE_MS, fadeMs)
        }
        try {
            controller.sendCustomCommand(CrossfadeControl.CMD_SET, args)
        } catch (e: Exception) {
            Log.w(TAG, "SET_CROSSFADE failed", e)
        }
    }

    private fun playTrackQueue(tracks: List<LocalPlaylistStore.Track>, startIndex: Int) {
        if (tracks.isEmpty()) return
        // Mixed audio/video playlists: keep same-kind continuity from the start track
        // so ExoPlayer avoids hard A/V renderer swaps mid-queue.
        var idx = startIndex.coerceIn(0, tracks.lastIndex)
        val kindVideo = tracks[idx].isVideo
        val sameKind = tracks.filter { it.isVideo == kindVideo }
        if (sameKind.isEmpty()) return
        idx = sameKind.indexOfFirst { it.uri == tracks[idx].uri }.let { if (it >= 0) it else 0 }
        val queue = sameKind
        val cur = queue[idx]
        val matchDur = _state.value.localItems.find { it.uri.toString() == cur.uri }?.durationMs ?: 0L
        val resumeMs = resumeStore.resumePositionMs(cur.uri, matchDur)
        withPlayer { p ->
            p.setMediaItems(
                queue.map {
                    mediaItem(
                        Uri.parse(it.uri),
                        it.title,
                        it.artist,
                        it.album,
                        it.isVideo,
                    )
                },
                idx,
                resumeMs,
            )
            p.prepare()
            p.play()
            queueStore.saveQueue(
                queue.map {
                    PlaybackQueueStore.Entry(
                        uri = it.uri,
                        title = it.title,
                        artist = it.artist,
                        album = it.album,
                        isVideo = it.isVideo,
                    )
                },
                idx,
                resumeMs,
            )
        }
        _state.update {
            it.copy(
                localTitle = cur.title,
                localArtist = cur.artist,
                localAlbum = cur.album,
                localQueueIndex = idx,
                localQueueSize = queue.size,
                localIsVideo = cur.isVideo,
                localPlaying = true,
                activeOutput = "This device",
                tab = AppTab.Local,
                connectOpen = false,
                error = "",
                resumeHint = if (resumeMs > 0L) "Resumed from ${fmt(resumeMs)}" else "",
            )
        }
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
        private const val PREF_REPEAT_PREFERRED = "local_repeat_preferred"
        private const val PREF_SHUFFLE = "local_shuffle"
        private const val PREF_SHUFFLE_PREFERRED = "local_shuffle_preferred"
        private const val PREF_HOME_FILTER = "home_filter"
        private const val PREF_HOME_FILTER_PREFERRED = "home_filter_preferred"
        private const val PREF_HOME_SEARCH = "home_search"
        private const val PREF_HOME_AZ = "home_az_letter"
        private const val PREF_AUDIO_FACET = "audio_facet"
        private val HOME_FILTERS = setOf(
            "all", "audio", "video", "recent", "top", "week", "month", "lists", "browse",
        )
        private val AUDIO_FACETS = setOf("artists", "albums", "tracks")
        private const val UNKNOWN_ARTIST = "Unknown artist"
        private const val UNKNOWN_ALBUM = "Unknown album"
        private val AUDIO_EXTS = setOf(
            "mp3", "flac", "m4a", "aac", "ogg", "opus", "wav", "wma", "aiff", "aif",
        )
        private val VIDEO_EXTS = setOf(
            "mp4", "mkv", "webm", "avi", "mov", "m4v", "wmv", "flv", "ts", "m2ts",
        )
        /** Soft duck when preferred headset unplugs while loud playback continues on speaker. */
        private const val ROUTE_FALLBACK_VOLUME_CAP = 40
    }
}
