package dev.voxhash.voxplayer.companion

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

/**
 * On-device playlist folders (manual) — no cloud. Smart lists are computed
 * elsewhere from library / play history.
 */
class LocalPlaylistStore(context: Context) {
    private val file = File(context.applicationContext.filesDir, "local_playlists.json")

    data class Track(
        val uri: String,
        val title: String,
        val artist: String,
        val album: String,
        val isVideo: Boolean,
    )

    data class Playlist(
        val id: String,
        val name: String,
        val tracks: List<Track>,
        val updatedAtMs: Long,
    )

    fun load(): List<Playlist> {
        if (!file.isFile) return emptyList()
        return try {
            val arr = JSONObject(file.readText()).optJSONArray("playlists") ?: JSONArray()
            buildList {
                for (i in 0 until arr.length()) {
                    val o = arr.optJSONObject(i) ?: continue
                    val id = o.optString("id", "").ifBlank { UUID.randomUUID().toString() }
                    val tracksArr = o.optJSONArray("tracks") ?: JSONArray()
                    val tracks = buildList {
                        for (j in 0 until tracksArr.length()) {
                            val t = tracksArr.optJSONObject(j) ?: continue
                            val uri = t.optString("uri", "").trim()
                            if (uri.isEmpty()) continue
                            add(
                                Track(
                                    uri = uri,
                                    title = t.optString("title", "").ifBlank {
                                        Uri.parse(uri).lastPathSegment ?: "Track"
                                    },
                                    artist = t.optString("artist", ""),
                                    album = t.optString("album", ""),
                                    isVideo = t.optBoolean("is_video", false),
                                ),
                            )
                        }
                    }
                    add(
                        Playlist(
                            id = id,
                            name = o.optString("name", "Playlist"),
                            tracks = tracks,
                            updatedAtMs = o.optLong("updated_at_ms", 0L),
                        ),
                    )
                }
            }.sortedByDescending { it.updatedAtMs }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun create(name: String): Playlist {
        val now = System.currentTimeMillis()
        val pl = Playlist(
            id = UUID.randomUUID().toString(),
            name = name.ifBlank { "Playlist" }.take(64),
            tracks = emptyList(),
            updatedAtMs = now,
        )
        save(listOf(pl) + load())
        return pl
    }

    fun rename(id: String, name: String) {
        val n = name.ifBlank { return }
        save(
            load().map {
                if (it.id == id) it.copy(name = n.take(64), updatedAtMs = System.currentTimeMillis())
                else it
            },
        )
    }

    fun delete(id: String) {
        save(load().filterNot { it.id == id })
    }

    fun addTrack(id: String, track: Track) {
        if (track.uri.isBlank()) return
        save(
            load().map { pl ->
                if (pl.id != id) return@map pl
                val tracks = pl.tracks.filterNot { it.uri == track.uri } + track
                pl.copy(tracks = tracks.take(MAX_TRACKS), updatedAtMs = System.currentTimeMillis())
            },
        )
    }

    fun removeTrack(id: String, uri: String) {
        save(
            load().map { pl ->
                if (pl.id != id) pl
                else pl.copy(
                    tracks = pl.tracks.filterNot { it.uri == uri },
                    updatedAtMs = System.currentTimeMillis(),
                )
            },
        )
    }

    private fun save(items: List<Playlist>) {
        val arr = JSONArray()
        items.take(MAX_PLAYLISTS).forEach { pl ->
            val tracks = JSONArray()
            pl.tracks.forEach { t ->
                tracks.put(
                    JSONObject()
                        .put("uri", t.uri)
                        .put("title", t.title)
                        .put("artist", t.artist)
                        .put("album", t.album)
                        .put("is_video", t.isVideo),
                )
            }
            arr.put(
                JSONObject()
                    .put("id", pl.id)
                    .put("name", pl.name)
                    .put("tracks", tracks)
                    .put("updated_at_ms", pl.updatedAtMs),
            )
        }
        file.writeText(JSONObject().put("playlists", arr).toString())
    }

    companion object {
        private const val MAX_PLAYLISTS = 40
        private const val MAX_TRACKS = 500

        const val SMART_NEW = "smart:new"
        const val SMART_RECENT = "smart:recent"
        const val SMART_TOP = "smart:top"
        const val SMART_SHORT = "smart:short"
    }
}
