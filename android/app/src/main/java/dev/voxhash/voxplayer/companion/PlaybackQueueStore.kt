package dev.voxhash.voxplayer.companion

import android.content.Context
import android.net.Uri
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.session.MediaSession
import org.json.JSONArray
import org.json.JSONObject

/**
 * Persists the on-device playlist (URI + metadata + index + position) so
 * [MediaSession.Callback.onPlaybackResumption] can restart after process death
 * and gapless queues survive service restarts. Local prefs only — no cloud, no GMS.
 */
class PlaybackQueueStore(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    data class Entry(
        val uri: String,
        val title: String,
        val artist: String = "",
        val album: String = "",
        val isVideo: Boolean = false,
    )

    data class Snapshot(
        val entries: List<Entry>,
        val index: Int,
        val positionMs: Long,
    ) {
        val current: Entry? get() = entries.getOrNull(index.coerceIn(0, (entries.size - 1).coerceAtLeast(0)))
    }

    fun saveQueue(entries: List<Entry>, index: Int, positionMs: Long) {
        if (entries.isEmpty()) {
            clear()
            return
        }
        val arr = JSONArray()
        entries.forEach { e ->
            arr.put(
                JSONObject()
                    .put("uri", e.uri)
                    .put("title", e.title)
                    .put("artist", e.artist)
                    .put("album", e.album)
                    .put("isVideo", e.isVideo),
            )
        }
        val safeIndex = index.coerceIn(0, entries.lastIndex)
        prefs.edit()
            .putString(KEY_QUEUE_JSON, arr.toString())
            .putInt(KEY_INDEX, safeIndex)
            .putLong(KEY_POSITION_MS, positionMs.coerceAtLeast(0L))
            // legacy single-item keys for older readers
            .putString(KEY_URI, entries[safeIndex].uri)
            .putString(KEY_TITLE, entries[safeIndex].title)
            .putBoolean(KEY_IS_VIDEO, entries[safeIndex].isVideo)
            .apply()
    }

    fun save(uri: String, title: String, positionMs: Long, isVideo: Boolean, artist: String = "", album: String = "") {
        saveQueue(listOf(Entry(uri, title, artist, album, isVideo)), 0, positionMs)
    }

    fun saveFromPlayer(player: Player) {
        if (player.mediaItemCount == 0) return
        val entries = buildList {
            for (i in 0 until player.mediaItemCount) {
                val item = player.getMediaItemAt(i)
                val uri = item.localConfiguration?.uri?.toString()
                    ?: item.requestMetadata.mediaUri?.toString()
                    ?: continue
                val md = item.mediaMetadata
                add(
                    Entry(
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
        if (entries.isEmpty()) return
        val index = player.currentMediaItemIndex.coerceIn(0, entries.lastIndex)
        saveQueue(entries, index, player.currentPosition.coerceAtLeast(0L))
    }

    fun load(): Snapshot? {
        val json = prefs.getString(KEY_QUEUE_JSON, null)
        if (!json.isNullOrBlank()) {
            return try {
                val arr = JSONArray(json)
                val entries = buildList {
                    for (i in 0 until arr.length()) {
                        val o = arr.optJSONObject(i) ?: continue
                        val uri = o.optString("uri", "").trim()
                        if (uri.isEmpty()) continue
                        add(
                            Entry(
                                uri = uri,
                                title = o.optString("title", "").ifBlank {
                                    Uri.parse(uri).lastPathSegment ?: "Media"
                                },
                                artist = o.optString("artist", ""),
                                album = o.optString("album", ""),
                                isVideo = o.optBoolean("isVideo", false),
                            ),
                        )
                    }
                }
                if (entries.isEmpty()) return null
                Snapshot(
                    entries = entries,
                    index = prefs.getInt(KEY_INDEX, 0).coerceIn(0, entries.lastIndex),
                    positionMs = prefs.getLong(KEY_POSITION_MS, 0L).coerceAtLeast(0L),
                )
            } catch (_: Exception) {
                null
            }
        }
        // Legacy single-item fallback
        val uri = prefs.getString(KEY_URI, null)?.trim().orEmpty()
        if (uri.isEmpty()) return null
        val entry = Entry(
            uri = uri,
            title = prefs.getString(KEY_TITLE, null)?.ifBlank { null }
                ?: Uri.parse(uri).lastPathSegment
                ?: "Media",
            isVideo = prefs.getBoolean(KEY_IS_VIDEO, false),
        )
        return Snapshot(
            entries = listOf(entry),
            index = 0,
            positionMs = prefs.getLong(KEY_POSITION_MS, 0L).coerceAtLeast(0L),
        )
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    fun toMediaItemsWithStartPosition(): MediaSession.MediaItemsWithStartPosition? {
        val snap = load() ?: return null
        if (snap.entries.isEmpty()) return null
        val items = snap.entries.map { e ->
            MediaItem.Builder()
                .setUri(e.uri)
                .setMediaMetadata(
                    MediaMetadata.Builder()
                        .setTitle(e.title)
                        .setArtist(e.artist.ifBlank { "VoxPlayer" })
                        .apply {
                            if (e.album.isNotBlank()) setAlbumTitle(e.album)
                            setMediaType(
                                if (e.isVideo) MediaMetadata.MEDIA_TYPE_VIDEO
                                else MediaMetadata.MEDIA_TYPE_MUSIC,
                            )
                        }
                        .setIsBrowsable(false)
                        .setIsPlayable(true)
                        .build(),
                )
                .build()
        }
        return MediaSession.MediaItemsWithStartPosition(
            items,
            snap.index.coerceIn(0, items.lastIndex),
            snap.positionMs,
        )
    }

    companion object {
        private const val PREFS = "voxplayer_playback_queue"
        private const val KEY_QUEUE_JSON = "queue_json"
        private const val KEY_INDEX = "index"
        private const val KEY_URI = "uri"
        private const val KEY_TITLE = "title"
        private const val KEY_POSITION_MS = "position_ms"
        private const val KEY_IS_VIDEO = "is_video"
    }
}
