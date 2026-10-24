package dev.voxhash.voxplayer.companion

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Scrobble-free on-device play history (no Last.fm / cloud). Tracks local
 * URI play counts and last-played timestamps for Recently / Most-played facets.
 */
class PlayHistoryStore(context: Context) {
    private val file = File(context.applicationContext.filesDir, "play_history.json")

    data class Entry(
        val uri: String,
        val title: String,
        val artist: String,
        val album: String,
        val isVideo: Boolean,
        val playCount: Int,
        val lastPlayedAtMs: Long,
    )

    fun load(): List<Entry> {
        if (!file.isFile) return emptyList()
        return try {
            val arr = JSONObject(file.readText()).optJSONArray("entries") ?: JSONArray()
            buildList {
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
                            isVideo = o.optBoolean("is_video", false),
                            playCount = o.optInt("play_count", 1).coerceAtLeast(1),
                            lastPlayedAtMs = o.optLong("last_played_at_ms", 0L),
                        ),
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun recentlyPlayed(limit: Int = 24): List<Entry> =
        load().sortedByDescending { it.lastPlayedAtMs }.take(limit)

    fun mostPlayed(limit: Int = 24): List<Entry> =
        load().sortedWith(
            compareByDescending<Entry> { it.playCount }.thenByDescending { it.lastPlayedAtMs },
        ).take(limit)

    /**
     * Record one meaningful listen for [uri]. Call once per media-item start
     * after a short playback threshold (not on every clock tick).
     */
    fun recordPlay(
        uri: String,
        title: String,
        artist: String = "",
        album: String = "",
        isVideo: Boolean = false,
    ) {
        if (uri.isBlank()) return
        val now = System.currentTimeMillis()
        val existing = load()
        val prev = existing.find { it.uri == uri }
        val next = existing.filterNot { it.uri == uri }.toMutableList()
        next.add(
            0,
            Entry(
                uri = uri,
                title = title.ifBlank { Uri.parse(uri).lastPathSegment ?: "Media" },
                artist = artist,
                album = album,
                isVideo = isVideo,
                playCount = (prev?.playCount ?: 0) + 1,
                lastPlayedAtMs = now,
            ),
        )
        save(next.take(MAX))
    }

    fun remove(uri: String) {
        save(load().filterNot { it.uri == uri })
    }

    fun clear() {
        if (file.exists()) file.delete()
    }

    private fun save(items: List<Entry>) {
        val arr = JSONArray()
        items.forEach { e ->
            arr.put(
                JSONObject()
                    .put("uri", e.uri)
                    .put("title", e.title)
                    .put("artist", e.artist)
                    .put("album", e.album)
                    .put("is_video", e.isVideo)
                    .put("play_count", e.playCount)
                    .put("last_played_at_ms", e.lastPlayedAtMs),
            )
        }
        file.writeText(JSONObject().put("entries", arr).toString())
    }

    companion object {
        private const val MAX = 200
    }
}
