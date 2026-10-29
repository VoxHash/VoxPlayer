package dev.voxhash.voxplayer.companion

import android.app.PendingIntent
import android.app.PictureInPictureParams
import android.app.RemoteAction
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.graphics.drawable.Icon
import android.os.Build
import android.os.Bundle
import android.util.Rational
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier

class MainActivity : ComponentActivity() {
    private val vm: PlayerViewModel by viewModels()

    private val pipReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                ACTION_PIP_PLAY_PAUSE -> vm.localPlayPause()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleViewIntent(intent)
        applyConnectExtras(intent)
        val pipOk = packageManager.hasSystemFeature(PackageManager.FEATURE_PICTURE_IN_PICTURE)
        vm.setPipAvailable(pipOk)
        val filter = IntentFilter(ACTION_PIP_PLAY_PAUSE)
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(pipReceiver, filter, RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("UnspecifiedRegisterReceiverFlag")
            registerReceiver(pipReceiver, filter)
        }
        enableEdgeToEdge()
        setContent {
            val state by vm.state.collectAsState()
            LaunchedEffect(state.localPlaying, state.localIsVideo, state.localTitle, state.pipAvailable) {
                refreshPipParams()
            }
            VoxTheme(mode = state.themeMode) {
                Surface(Modifier.fillMaxSize(), color = VoxColors.BgApp) {
                    VoxPlayerApp(vm)
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
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

    override fun onUserLeaveHint() {
        super.onUserLeaveHint()
        // Pre-Android 12: home/recents → enter PiP when local video is playing.
        // Android 12+: auto-enter is driven by PictureInPictureParams.setAutoEnterEnabled.
        if (Build.VERSION.SDK_INT < 31 && vm.canEnterPip() && vm.state.value.localPlaying) {
            enterPictureInPictureMode(buildPipParams())
        }
    }

    override fun onPictureInPictureModeChanged(
        isInPictureInPictureMode: Boolean,
        newConfig: Configuration,
    ) {
        super.onPictureInPictureModeChanged(isInPictureInPictureMode, newConfig)
        vm.setPipActive(isInPictureInPictureMode)
        if (!isInPictureInPictureMode) {
            refreshPipParams()
        }
    }

    override fun onDestroy() {
        try {
            unregisterReceiver(pipReceiver)
        } catch (_: Exception) {
        }
        DlnaCastControl.cleanup()
        super.onDestroy()
    }

    /** Enter system PiP for the current local video; returns false when ineligible. */
    fun enterPip(): Boolean {
        if (!vm.state.value.pipAvailable) {
            vm.flashStatus("Picture-in-picture not available on this device")
            return false
        }
        if (!vm.canEnterPip()) {
            vm.flashStatus("Picture-in-picture needs local video")
            return false
        }
        return try {
            enterPictureInPictureMode(buildPipParams())
        } catch (e: Exception) {
            vm.flashStatus("Picture-in-picture failed")
            false
        }
    }

    fun refreshPipParams() {
        if (!vm.state.value.pipAvailable) return
        try {
            setPictureInPictureParams(buildPipParams())
        } catch (_: Exception) {
        }
    }

    private fun buildPipParams(): PictureInPictureParams {
        val playing = vm.state.value.localPlaying
        val builder = PictureInPictureParams.Builder()
            .setAspectRatio(Rational(16, 9))
            .setActions(listOf(playPauseRemoteAction(playing)))
        if (Build.VERSION.SDK_INT >= 31) {
            builder.setAutoEnterEnabled(vm.canEnterPip() && playing)
            builder.setSeamlessResizeEnabled(true)
        }
        return builder.build()
    }

    private fun playPauseRemoteAction(playing: Boolean): RemoteAction {
        val intent = Intent(ACTION_PIP_PLAY_PAUSE).setPackage(packageName)
        val pending = PendingIntent.getBroadcast(
            this,
            PIP_REQUEST_CODE,
            intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val iconRes = if (playing) {
            android.R.drawable.ic_media_pause
        } else {
            android.R.drawable.ic_media_play
        }
        val title = if (playing) "Pause" else "Play"
        return RemoteAction(
            Icon.createWithResource(this, iconRes),
            title,
            title,
            pending,
        )
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
        val sheet = extras.getString("player_sheet").orEmpty().lowercase()
        if (sheet.isNotBlank()) {
            val mapped = when (sheet) {
                "settings" -> PlayerSheet.Settings
                "speed" -> PlayerSheet.Speed
                "captions" -> PlayerSheet.Captions
                "more" -> PlayerSheet.More
                "quality" -> PlayerSheet.Quality
                "storage" -> PlayerSheet.Storage
                "track", "track_actions" -> PlayerSheet.TrackActions
                "queue", "up_next" -> PlayerSheet.Queue
                "favorites", "favourite", "bookmarks" -> PlayerSheet.Favorites
                "sleep" -> PlayerSheet.Sleep
                "about", "help" -> PlayerSheet.About
                "codec_policy", "policy" -> PlayerSheet.CodecPolicy
                else -> null
            }
            if (mapped != null) vm.openPlayerSheet(mapped)
        }
        val stage = extras.getBoolean("now_playing_stage", false) ||
            extras.getString("now_playing_stage").equals("1", true) ||
            extras.getString("now_playing_stage").equals("true", true)
        if (stage) vm.openNowPlayingTab()
        val dest = extras.getString("primary_dest").orEmpty().lowercase()
        if (dest.isNotBlank()) {
            val mapped = when (dest) {
                "home" -> PrimaryDest.Home
                "video" -> PrimaryDest.Video
                "audio" -> PrimaryDest.Audio
                "browse" -> PrimaryDest.Browse
                "lists" -> PrimaryDest.Lists
                "more" -> PrimaryDest.More
                else -> null
            }
            if (mapped != null) {
                android.util.Log.i("VoxPlayerBT", "setPrimaryDest=$dest")
                vm.setPrimaryDest(mapped)
            }
        }
        val transport = extras.getString("transport").orEmpty().lowercase()
        when (transport) {
            "next" -> {
                android.util.Log.i("VoxPlayerBT", "transport=next")
                vm.localNext()
            }
            "prev", "previous" -> {
                android.util.Log.i("VoxPlayerBT", "transport=prev")
                vm.localPrev()
            }
            "play_pause", "playpause" -> {
                android.util.Log.i("VoxPlayerBT", "transport=play_pause")
                vm.localPlayPause()
            }
            "seek_fwd", "forward" -> {
                android.util.Log.i("VoxPlayerBT", "transport=seek_fwd")
                vm.seekLocal(vm.state.value.localPositionMs + 15_000L)
            }
            "seek_back", "back" -> {
                android.util.Log.i("VoxPlayerBT", "transport=seek_back")
                vm.seekLocal((vm.state.value.localPositionMs - 15_000L).coerceAtLeast(0L))
            }
        }
        if (extras.containsKey("seek_ms")) {
            val ms = extras.getLong("seek_ms", -1L).takeIf { it >= 0L }
                ?: extras.getInt("seek_ms", -1).toLong().takeIf { it >= 0L }
            if (ms != null) {
                android.util.Log.i("VoxPlayerBT", "seek_ms=$ms")
                vm.seekLocal(ms)
            }
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

    companion object {
        const val ACTION_PIP_PLAY_PAUSE = "dev.voxhash.voxplayer.companion.PIP_PLAY_PAUSE"
        private const val PIP_REQUEST_CODE = 1001
    }
}
