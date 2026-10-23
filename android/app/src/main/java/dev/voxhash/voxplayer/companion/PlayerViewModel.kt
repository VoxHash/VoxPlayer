package dev.voxhash.voxplayer.companion

import android.Manifest
import android.app.Application
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
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

data class PlayerUiState(
    val tab: AppTab = AppTab.Local,
    val localItems: List<LocalMediaItem> = emptyList(),
    val localFilter: String = "all", // all|audio|video
    val permissionNeeded: Boolean = false,
    val localTitle: String = "(nothing loaded)",
    val localPlaying: Boolean = false,
    val localPositionLabel: String = "0:00 / 0:00",
    val localIsVideo: Boolean = false,
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
    val activeOutput: String = "This device", // "This device" or "Desktop · host" / "Desktop · BT"
    val syncedPlaylists: List<SyncStore.SyncedPlaylist> = emptyList(),
    val syncedFeeds: List<SyncStore.SyncedFeed> = emptyList(),
    val syncBusy: Boolean = false,
    val syncMessage: String = "",
)

class PlayerViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = app.getSharedPreferences("voxplayer", Context.MODE_PRIVATE)
    private val syncStore = SyncStore(app)
    private val bt = BluetoothControl(app)
    private val _state = MutableStateFlow(
        PlayerUiState(
            remoteHost = prefs.getString("host", "192.168.1.1") ?: "192.168.1.1",
            remotePort = prefs.getString("port", "17890") ?: "17890",
            syncedPlaylists = syncStore.loadPlaylists(),
            syncedFeeds = syncStore.loadPodcasts(),
        ),
    )
    val state: StateFlow<PlayerUiState> = _state.asStateFlow()

    val player: ExoPlayer = ExoPlayer.Builder(app).build().also { p ->
        p.addListener(object : Player.Listener {
            override fun onIsPlayingChanged(isPlaying: Boolean) {
                _state.update {
                    it.copy(
                        localPlaying = isPlaying,
                        activeOutput = if (isPlaying) "This device" else it.activeOutput,
                    )
                }
            }
        })
    }

    private var remotePoll: Job? = null
    private var localTick: Job? = null

    init {
        localTick = viewModelScope.launch {
            while (isActive) {
                refreshLocalClock()
                delay(500)
            }
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

    fun playLocal(item: LocalMediaItem) {
        player.stop()
        player.setMediaItem(MediaItem.fromUri(item.uri))
        player.prepare()
        player.play()
        _state.update {
            it.copy(
                localTitle = item.title,
                localIsVideo = item.isVideo,
                localPlaying = true,
                activeOutput = "This device",
                tab = AppTab.Local,
                connectOpen = false,
            )
        }
    }

    fun playUri(uri: Uri, title: String = uri.lastPathSegment ?: "Media", isVideo: Boolean = true) {
        player.stop()
        player.setMediaItem(MediaItem.fromUri(uri))
        player.prepare()
        player.play()
        _state.update {
            it.copy(
                localTitle = title,
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
        if (player.isPlaying) player.pause() else player.play()
    }

    fun localStop() {
        player.stop()
        _state.update { it.copy(localPlaying = false, localTitle = "(nothing loaded)") }
    }

    fun localSeekBy(ms: Long) {
        val pos = (player.currentPosition + ms).coerceAtLeast(0L)
        player.seekTo(pos)
    }

    private fun refreshLocalClock() {
        val pos = player.currentPosition.coerceAtLeast(0L)
        val dur = player.duration.coerceAtLeast(0L).let { if (it < 0) 0 else it }
        _state.update {
            it.copy(
                localPlaying = player.isPlaying,
                localPositionLabel = "${fmt(pos)} / ${fmt(dur)}",
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
        if (player.isPlaying) player.pause()
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
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(error = "", syncMessage = "Connecting Bluetooth…") }
            try {
                remotePoll?.cancel()
                withContext(Dispatchers.IO) {
                    bt.connect(address)
                }
                if (player.isPlaying) player.pause()
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
                startRemotePoll()
            } catch (e: Exception) {
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
        player.release()
        super.onCleared()
    }
}
