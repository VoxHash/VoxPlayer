package dev.voxhash.voxplayer.companion

import android.content.Context
import android.net.Uri
import org.json.JSONObject
import java.io.File

/**
 * Silent per-URI last-position memory (no cloud). Distinct from [BookmarkStore]:
 * bookmarks are an explicit Now Playing list; this store auto-seeks when the
 * user opens the same track again from Home / Lists / SAF.
 */
class TrackResumeStore(context: Context) {
    private val file = File(context.applicationContext.filesDir, "track_resume.json")

    data class Entry(
        val uri: String,
        val positionMs: Long,
        val updatedAtMs: Long,
    )

    fun loadMap(): Map<String, Entry> {
        if (!file.isFile) return emptyMap()
        return try {
            val root = JSONObject(file.readText())
            val obj = root.optJSONObject("positions") ?: return emptyMap()
            buildMap {
                obj.keys().forEach { key ->
                    val o = obj.optJSONObject(key) ?: return@forEach
                    val uri = key.trim()
                    if (uri.isEmpty()) return@forEach
                    put(
                        uri,
                        Entry(
                            uri = uri,
                            positionMs = o.optLong("position_ms", 0L).coerceAtLeast(0L),
                            updatedAtMs = o.optLong("updated_at_ms", 0L),
                        ),
                    )
                }
            }
        } catch (_: Exception) {
            emptyMap()
        }
    }

    fun get(uri: String): Long? {
        val e = loadMap()[uri.trim()] ?: return null
        return e.positionMs.takeIf { it >= MIN_SAVE_MS }
    }

    /**
     * Position to seek when starting [uri], or `0` if none / near start / near end.
     * [durationMs] ≤ 0 means duration unknown — still resume if mid-track.
     */
    fun resumePositionMs(uri: String, durationMs: Long = 0L): Long {
        val pos = get(uri) ?: return 0L
        if (pos < MIN_SAVE_MS) return 0L
        if (durationMs > 0L) {
            if (pos + NEAR_END_MS >= durationMs) return 0L
            if (durationMs < MIN_TRACK_MS) return 0L
        }
        return pos
    }

    fun save(uri: String, positionMs: Long, durationMs: Long = 0L) {
        val u = uri.trim()
        if (u.isEmpty()) return
        if (positionMs < MIN_SAVE_MS) return
        if (durationMs > 0L && positionMs + NEAR_END_MS >= durationMs) {
            clear(u)
            return
        }
        val map = loadMap().toMutableMap()
        map[u] = Entry(u, positionMs, System.currentTimeMillis())
        // Cap by recency
        val trimmed = map.values.sortedByDescending { it.updatedAtMs }.take(MAX).associateBy { it.uri }
        saveMap(trimmed)
    }

    fun clear(uri: String) {
        val map = loadMap().toMutableMap()
        if (map.remove(uri.trim()) != null) saveMap(map)
    }

    fun clearAll() {
        if (file.exists()) file.delete()
    }

    private fun saveMap(map: Map<String, Entry>) {
        val positions = JSONObject()
        map.values.forEach { e ->
            positions.put(
                e.uri,
                JSONObject()
                    .put("position_ms", e.positionMs)
                    .put("updated_at_ms", e.updatedAtMs)
                    .put("title", Uri.parse(e.uri).lastPathSegment ?: ""),
            )
        }
        file.writeText(JSONObject().put("positions", positions).toString())
    }

    companion object {
        private const val MAX = 200
        const val MIN_SAVE_MS = 5_000L
        private const val NEAR_END_MS = 12_000L
        private const val MIN_TRACK_MS = 30_000L
    }
}
