package dev.voxhash.voxplayer.companion

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

data class CompanionUiState(
    val host: String = "127.0.0.1",
    val port: String = "17890",
    val connected: Boolean = false,
    val error: String = "",
    val playing: Boolean = false,
    val title: String = "(nothing loaded)",
    val positionLabel: String = "0:00 / 0:00",
    val volume: Int = 50,
    val version: String = "",
    val library: List<DaemonClient.LibraryItem> = emptyList(),
    val libraryTotal: Int = 0,
)

class CompanionViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = app.getSharedPreferences("voxplayer_companion", Context.MODE_PRIVATE)
    private val _state = MutableStateFlow(
        CompanionUiState(
            host = prefs.getString("host", "127.0.0.1") ?: "127.0.0.1",
            port = prefs.getString("port", "17890") ?: "17890",
        ),
    )
    val state: StateFlow<CompanionUiState> = _state.asStateFlow()

    private var pollJob: Job? = null

    fun updateHost(value: String) = _state.update { it.copy(host = value.trim()) }
    fun updatePort(value: String) = _state.update { it.copy(port = value.trim()) }

    fun applyEndpoint(host: String, port: String, autoconnect: Boolean) {
        val h = host.trim().ifBlank { _state.value.host }
        val p = port.trim().ifBlank { _state.value.port }
        _state.update { it.copy(host = h, port = p) }
        prefs.edit().putString("host", h).putString("port", p).apply()
        if (autoconnect) connect()
    }

    fun connect() {
        val s = _state.value
        prefs.edit().putString("host", s.host).putString("port", s.port).apply()
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            refreshLibrary()
            while (isActive) {
                refreshOnce()
                delay(1000)
            }
        }
    }

    fun disconnect() {
        pollJob?.cancel()
        pollJob = null
        _state.update { it.copy(connected = false, error = "", library = emptyList(), libraryTotal = 0) }
    }

    fun refreshLibrary() = viewModelScope.launch {
        try {
            val page = withContext(Dispatchers.IO) { client().library(limit = 200, offset = 0) }
            _state.update {
                it.copy(library = page.items, libraryTotal = page.total, error = "")
            }
        } catch (e: Exception) {
            _state.update { it.copy(error = e.message ?: e.toString()) }
        }
    }

    fun openLibraryItem(path: String) = runAction { it.open(path) }

    fun playPause() = runAction { it.playPause() }
    fun stop() = runAction { it.stop() }
    fun next() = runAction { it.next() }
    fun previous() = runAction { it.previous() }
    fun seekBack() = runAction { it.seekRelative(-5000) }
    fun seekFwd() = runAction { it.seekRelative(5000) }
    fun volumeDown() = runAction { c ->
        val v = (_state.value.volume - 5).coerceAtLeast(0)
        c.volume(v)
    }
    fun volumeUp() = runAction { c ->
        val v = (_state.value.volume + 5).coerceAtMost(200)
        c.volume(v)
    }

    private fun client(): DaemonClient {
        val s = _state.value
        return DaemonClient("http://${s.host}:${s.port}")
    }

    private fun runAction(block: (DaemonClient) -> Unit) {
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) { block(client()) }
                refreshOnce()
            } catch (e: Exception) {
                _state.update { it.copy(error = e.message ?: e.toString(), connected = false) }
            }
        }
    }

    private suspend fun refreshOnce() {
        try {
            val st = withContext(Dispatchers.IO) { client().status() }
            val name = File(st.path).name.ifBlank { "(nothing loaded)" }
            _state.update {
                it.copy(
                    connected = true,
                    error = "",
                    playing = st.playing,
                    title = name,
                    positionLabel = "${fmt(st.positionMs)} / ${fmt(st.durationMs)}",
                    volume = st.volumePercent,
                    version = st.version,
                )
            }
        } catch (e: Exception) {
            _state.update {
                it.copy(connected = false, error = e.message ?: e.toString())
            }
        }
    }

    private fun fmt(ms: Long): String {
        val sec = (ms / 1000).coerceAtLeast(0)
        val m = sec / 60
        val s = sec % 60
        return "%d:%02d".format(m, s)
    }

    override fun onCleared() {
        pollJob?.cancel()
        super.onCleared()
    }
}
