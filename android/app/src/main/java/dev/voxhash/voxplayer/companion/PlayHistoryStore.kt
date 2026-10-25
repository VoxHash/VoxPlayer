package dev.voxhash.voxplayer.companion

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Scrobble-free on-device play history (no Last.fm / cloud). Tracks local
 * URI play counts, last-played timestamps, and a rolling listen-event log for
 * week / month facets.
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

    data class ListenEvent(
        val uri: String,
        val title: String,
        val artist: String,
        val album: String,
        val isVideo: Boolean,
        val atMs: Long,
    )

    /** Aggregated listens for a calendar window (7d / 30d). */
    data class PeriodFacet(
        val label: String,
        val listenCount: Int,
        val uniqueTracks: Int,
        val topArtist: String,
        val tracks: List<Entry>,
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

    fun loadEvents(): List<ListenEvent> {
        if (!file.isFile) return emptyList()
        return try {
            val arr = JSONObject(file.readText()).optJSONArray("events") ?: JSONArray()
            buildList {
                for (i in 0 until arr.length()) {
                    val o = arr.optJSONObject(i) ?: continue
                    val uri = o.optString("uri", "").trim()
                    if (uri.isEmpty()) continue
                    add(
                        ListenEvent(
                            uri = uri,
                            title = o.optString("title", "").ifBlank {
                                Uri.parse(uri).lastPathSegment ?: "Media"
                            },
                            artist = o.optString("artist", ""),
                            album = o.optString("album", ""),
                            isVideo = o.optBoolean("is_video", false),
                            atMs = o.optLong("at_ms", 0L),
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

    fun weekFacet(limit: Int = 24): PeriodFacet = periodFacet(days = 7, label = "This week", limit = limit)

    fun monthFacet(limit: Int = 24): PeriodFacet = periodFacet(days = 30, label = "This month", limit = limit)

    private fun periodFacet(days: Int, label: String, limit: Int): PeriodFacet {
        val since = System.currentTimeMillis() - days * DAY_MS
        val window = loadEvents().filter { it.atMs >= since }
        if (window.isEmpty()) {
            return PeriodFacet(label, 0, 0, "", emptyList())
        }
        val byUri = linkedMapOf<String, MutableList<ListenEvent>>()
        window.forEach { e -> byUri.getOrPut(e.uri) { mutableListOf() }.add(e) }
        val tracks = byUri.map { (uri, evs) ->
            val latest = evs.maxBy { it.atMs }
            Entry(
                uri = uri,
                title = latest.title,
                artist = latest.artist,
                album = latest.album,
                isVideo = latest.isVideo,
                playCount = evs.size,
                lastPlayedAtMs = latest.atMs,
            )
        }.sortedWith(
            compareByDescending<Entry> { it.playCount }.thenByDescending { it.lastPlayedAtMs },
        )
        val artistCounts = mutableMapOf<String, Int>()
        window.forEach { e ->
            val a = e.artist.trim()
            if (a.isNotEmpty()) artistCounts[a] = (artistCounts[a] ?: 0) + 1
        }
        val topArtist = artistCounts.maxByOrNull { it.value }?.key.orEmpty()
        return PeriodFacet(
            label = label,
            listenCount = window.size,
            uniqueTracks = byUri.size,
            topArtist = topArtist,
            tracks = tracks.take(limit),
        )
    }

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
        val events = loadEvents().toMutableList()
        events.add(
            0,
            ListenEvent(
                uri = uri,
                title = title.ifBlank { Uri.parse(uri).lastPathSegment ?: "Media" },
                artist = artist,
                album = album,
                isVideo = isVideo,
                atMs = now,
            ),
        )
        val pruneBefore = now - RETAIN_DAYS * DAY_MS
        val pruned = events.filter { it.atMs >= pruneBefore }.take(MAX_EVENTS)
        save(next.take(MAX), pruned)
    }

    fun remove(uri: String) {
        save(
            load().filterNot { it.uri == uri },
            loadEvents().filterNot { it.uri == uri },
        )
    }

    fun clear() {
        if (file.exists()) file.delete()
    }

    private fun save(items: List<Entry>, events: List<ListenEvent>) {
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
        val evArr = JSONArray()
        events.forEach { e ->
            evArr.put(
                JSONObject()
                    .put("uri", e.uri)
                    .put("title", e.title)
                    .put("artist", e.artist)
                    .put("album", e.album)
                    .put("is_video", e.isVideo)
                    .put("at_ms", e.atMs),
            )
        }
        file.writeText(
            JSONObject()
                .put("entries", arr)
                .put("events", evArr)
                .toString(),
        )
    }

    companion object {
        private const val MAX = 200
        private const val MAX_EVENTS = 2000
        private const val RETAIN_DAYS = 90L
        private const val DAY_MS = 24L * 60L * 60L * 1000L
    }
}
