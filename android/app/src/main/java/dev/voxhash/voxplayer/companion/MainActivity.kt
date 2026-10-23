package dev.voxhash.voxplayer.companion

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    private val vm: CompanionViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val extras = intent?.extras
        if (extras != null) {
            val host = extras.getString("host").orEmpty()
            val port = extras.getString("port").orEmpty()
            val autoconnect = extras.getBoolean("autoconnect", false) ||
                extras.getString("autoconnect").equals("1", ignoreCase = true) ||
                extras.getString("autoconnect").equals("true", ignoreCase = true)
            if (host.isNotBlank() || port.isNotBlank() || autoconnect) {
                vm.applyEndpoint(host, port, autoconnect)
            }
        }
        enableEdgeToEdge()
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = Color(0xFF5B8DEF),
                    background = Color(0xFF12141A),
                    surface = Color(0xFF1A2030),
                ),
            ) {
                Surface(Modifier.fillMaxSize()) {
                    CompanionScreen(vm)
                }
            }
        }
    }
}

@Composable
fun CompanionScreen(vm: CompanionViewModel) {
    val state by vm.state.collectAsState()
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            "VoxPlayer",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.SemiBold,
        )
        Text(
            "LAN companion — browse the desktop library and remote-control the daemon. No Google Play Services.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
        )
        OutlinedTextField(
            value = state.host,
            onValueChange = vm::updateHost,
            label = { Text("Desktop host (LAN IP or 127.0.0.1 via adb reverse)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        OutlinedTextField(
            value = state.port,
            onValueChange = vm::updatePort,
            label = { Text("Daemon port") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = vm::connect) { Text("Connect") }
            Button(onClick = vm::disconnect) { Text("Disconnect") }
            Button(onClick = vm::refreshLibrary) { Text("Refresh library") }
        }
        Text(
            if (state.connected) "Connected · desktop v${state.version.ifBlank { "?" }}"
            else "Disconnected",
            color = if (state.connected) Color(0xFF7DCEA0) else Color(0xFFE26D6D),
        )
        if (state.error.isNotBlank()) {
            Text(state.error, color = Color(0xFFE26D6D))
        }
        Spacer(Modifier.height(8.dp))
        Text(
            "[${if (state.playing) "PLAYING" else "PAUSED"}] ${state.title}",
            style = MaterialTheme.typography.titleMedium,
        )
        Text(state.positionLabel + " · vol ${state.volume}%")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = vm::previous, modifier = Modifier.weight(1f)) { Text("Prev") }
            Button(onClick = vm::playPause, modifier = Modifier.weight(1f)) { Text("Play/Pause") }
            Button(onClick = vm::next, modifier = Modifier.weight(1f)) { Text("Next") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = vm::stop, modifier = Modifier.weight(1f)) { Text("Stop") }
            Button(onClick = vm::seekBack, modifier = Modifier.weight(1f)) { Text("−5s") }
            Button(onClick = vm::seekFwd, modifier = Modifier.weight(1f)) { Text("+5s") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = vm::volumeDown, modifier = Modifier.weight(1f)) { Text("Vol −") }
            Button(onClick = vm::volumeUp, modifier = Modifier.weight(1f)) { Text("Vol +") }
        }
        Spacer(Modifier.height(8.dp))
        Text(
            "Library (${state.library.size}/${state.libraryTotal})",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
        )
        if (state.library.isEmpty()) {
            Text(
                "Connect to load indexed desktop titles (read-only).",
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f),
            )
        } else {
            state.library.take(80).forEach { item ->
                Text(
                    item.title,
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { vm.openLibraryItem(item.path) }
                        .padding(vertical = 6.dp),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            if (state.library.size > 80) {
                Text(
                    "… ${state.library.size - 80} more (tap Refresh after scrolling desktop roots)",
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f),
                )
            }
        }
        Text(
            "Desktop LAN: VOXPLAYER_DAEMON_ALLOW_LAN=1 and VOXPLAYER_DAEMON_HOST=0.0.0.0. " +
                "USB debug: adb reverse tcp:17890 tcp:17890 then host 127.0.0.1. " +
                "GrapheneOS: grant network only; no cloud account.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f),
        )
    }
}
