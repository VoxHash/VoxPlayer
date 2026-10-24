package dev.voxhash.voxplayer.companion

import android.content.Context
import android.net.Uri
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.session.MediaSession

/**
 * Persists the last on-device media item + position so
 * [MediaSession.Callback.onPlaybackResumption] can restart after process death
 * (headset media button / system resume). Local prefs only — no cloud, no GMS.
 */
class PlaybackQueueStore(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    data class Snapshot(
        val uri: String,
        val title: String,
        val positionMs: Long,
        val isVideo: Boolean,
    )

    fun save(uri: String, title: String, positionMs: Long, isVideo: Boolean) {
        if (uri.isBlank()) return
        prefs.edit()
            .putString(KEY_URI, uri)
            .putString(KEY_TITLE, title)
            .putLong(KEY_POSITION_MS, positionMs.coerceAtLeast(0L))
            .putBoolean(KEY_IS_VIDEO, isVideo)
            .apply()
    }

    fun saveFromPlayer(player: androidx.media3.common.Player, isVideo: Boolean = false) {
        val item = player.currentMediaItem ?: return
        val uri = item.localConfiguration?.uri?.toString() ?: item.requestMetadata.mediaUri?.toString()
        if (uri.isNullOrBlank()) return
        val title = item.mediaMetadata.title?.toString()
            ?: Uri.parse(uri).lastPathSegment
            ?: "Media"
        save(uri, title, player.currentPosition.coerceAtLeast(0L), isVideo)
    }

    fun load(): Snapshot? {
        val uri = prefs.getString(KEY_URI, null)?.trim().orEmpty()
        if (uri.isEmpty()) return null
        return Snapshot(
            uri = uri,
            title = prefs.getString(KEY_TITLE, null)?.ifBlank { null }
                ?: Uri.parse(uri).lastPathSegment
                ?: "Media",
            positionMs = prefs.getLong(KEY_POSITION_MS, 0L).coerceAtLeast(0L),
            isVideo = prefs.getBoolean(KEY_IS_VIDEO, false),
        )
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    fun toMediaItemsWithStartPosition(): MediaSession.MediaItemsWithStartPosition? {
        val snap = load() ?: return null
        val item = MediaItem.Builder()
            .setUri(snap.uri)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(snap.title)
                    .setArtist("VoxPlayer")
                    .setIsBrowsable(false)
                    .setIsPlayable(true)
                    .build(),
            )
            .build()
        return MediaSession.MediaItemsWithStartPosition(
            listOf(item),
            /* startIndex = */ 0,
            snap.positionMs,
        )
    }

    companion object {
        private const val PREFS = "voxplayer_playback_queue"
        private const val KEY_URI = "uri"
        private const val KEY_TITLE = "title"
        private const val KEY_POSITION_MS = "position_ms"
        private const val KEY_IS_VIDEO = "is_video"
    }
}
