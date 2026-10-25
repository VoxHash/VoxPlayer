package dev.voxhash.voxplayer.companion

import android.content.Intent
import android.content.res.Configuration
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier

class MainActivity : ComponentActivity() {
    private val vm: PlayerViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleViewIntent(intent)
        applyConnectExtras(intent)
        enableEdgeToEdge()
        setContent {
            VoxTheme {
                Surface(Modifier.fillMaxSize(), color = VoxColors.BgApp) {
                    VoxPlayerApp(vm)
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleViewIntent(intent)
        applyConnectExtras(intent)
    }

    override fun onResume() {
        super.onResume()
        // Quest panel refocus / phone return: re-bind preferred sink + EQ/volume.
        vm.reapplyLocalAudio()
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        // Fold / multi-window / Quest panel resize — keep playback + audio chain alive.
        vm.onWindowLayoutChanged(
            multiWindow = isInMultiWindowMode,
            orientation = newConfig.orientation,
        )
        vm.reapplyLocalAudio()
    }

    override fun onMultiWindowModeChanged(isInMultiWindowMode: Boolean, newConfig: Configuration) {
        super.onMultiWindowModeChanged(isInMultiWindowMode, newConfig)
        vm.onWindowLayoutChanged(multiWindow = isInMultiWindowMode, orientation = newConfig.orientation)
        vm.reapplyLocalAudio()
    }

    private fun applyConnectExtras(intent: Intent?) {
        val extras = intent?.extras ?: return
        val host = extras.getString("host").orEmpty()
        val port = extras.getString("port").orEmpty()
        val autoconnect = extras.getBoolean("autoconnect", false) ||
            extras.getString("autoconnect").equals("1", true) ||
            extras.getString("autoconnect").equals("true", true)
        if (host.isNotBlank() || port.isNotBlank() || autoconnect) {
            if (host.isNotBlank()) vm.updateRemoteHost(host)
            if (port.isNotBlank()) vm.updateRemotePort(port)
            if (autoconnect) vm.connectManual()
        }
        val btAddress = extras.getString("bt_address").orEmpty()
        val btName = extras.getString("bt_name").orEmpty().ifBlank { "Desktop" }
        val btConnect = extras.getBoolean("bt_connect", false) ||
            extras.getString("bt_connect").equals("1", true) ||
            extras.getString("bt_connect").equals("true", true)
        if (btAddress.isNotBlank() && btConnect) {
            vm.connectBluetooth(btAddress, btName)
        }
    }

    private fun handleViewIntent(intent: Intent?) {
        if (intent?.action == Intent.ACTION_VIEW) {
            val uri = intent.data ?: return
            val mime = intent.type ?: contentResolver.getType(uri) ?: ""
            val isVideo = mime.startsWith("video")
            vm.playUri(uri, uri.lastPathSegment ?: "Media", isVideo)
        }
    }
}
