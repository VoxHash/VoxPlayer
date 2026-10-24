package dev.voxhash.voxplayer.companion

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Local per-URI resume bookmarks (no cloud). Mirrors desktop playback-companion
 * bookmark resume: store title + position for a content/file URI.
 */
class BookmarkStore(context: Context) {
    private val file = File(context.applicationContext.filesDir, "bookmarks.json")

    data class Bookmark(
        val uri: String,
        val title: String,
        val positionMs: Long,
        val isVideo: Boolean,
        val updatedAtMs: Long,
    )

    fun load(): List<Bookmark> {
        if (!file.isFile) return emptyList()
        return try {
            val arr = JSONObject(file.readText()).optJSONArray("bookmarks") ?: JSONArray()
            buildList {
                for (i in 0 until arr.length()) {
                    val o = arr.optJSONObject(i) ?: continue
                    val uri = o.optString("uri", "").trim()
                    if (uri.isEmpty()) continue
                    add(
                        Bookmark(
                            uri = uri,
                            title = o.optString("title", "").ifBlank {
                                Uri.parse(uri).lastPathSegment ?: "Bookmark"
                            },
                            positionMs = o.optLong("position_ms", 0L).coerceAtLeast(0L),
                            isVideo = o.optBoolean("is_video", false),
                            updatedAtMs = o.optLong("updated_at_ms", 0L),
                        ),
                    )
                }
            }.sortedByDescending { it.updatedAtMs }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun upsert(uri: String, title: String, positionMs: Long, isVideo: Boolean) {
        if (uri.isBlank() || positionMs < 1_500L) return
        val now = System.currentTimeMillis()
        val next = load().filterNot { it.uri == uri }.toMutableList()
        next.add(
            0,
            Bookmark(
                uri = uri,
                title = title.ifBlank { Uri.parse(uri).lastPathSegment ?: "Bookmark" },
                positionMs = positionMs,
                isVideo = isVideo,
                updatedAtMs = now,
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

    private fun save(items: List<Bookmark>) {
        val arr = JSONArray()
        items.forEach { b ->
            arr.put(
                JSONObject()
                    .put("uri", b.uri)
                    .put("title", b.title)
                    .put("position_ms", b.positionMs)
                    .put("is_video", b.isVideo)
                    .put("updated_at_ms", b.updatedAtMs),
            )
        }
        file.writeText(JSONObject().put("bookmarks", arr).toString())
    }

    companion object {
        private const val MAX = 40
    }
}
