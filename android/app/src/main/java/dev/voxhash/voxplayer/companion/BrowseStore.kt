package dev.voxhash.voxplayer.companion

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject

/**
 * On-device Browse favorites (SAF tree URIs). No cloud.
 * Built-in MediaStore shortcuts (Download / Music / …) live in the UI, not here.
 */
object BrowseStore {
    private const val PREFS = "voxplayer_browse"
    private const val KEY_FAVORITES = "favorites_json"

    data class FavoriteFolder(
        val id: String,
        val label: String,
        val treeUri: String,
    )

    fun loadFavorites(context: Context): List<FavoriteFolder> {
        val raw = context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_FAVORITES, null)
            ?.takeIf { it.isNotBlank() }
            ?: return emptyList()
        return try {
            val arr = JSONArray(raw)
            buildList {
                for (i in 0 until arr.length()) {
                    val o = arr.optJSONObject(i) ?: continue
                    val uri = o.optString("treeUri").trim()
                    val label = o.optString("label").trim()
                    val id = o.optString("id").trim().ifBlank { uri }
                    if (uri.isBlank() || label.isBlank()) continue
                    add(FavoriteFolder(id = id, label = label, treeUri = uri))
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun saveFavorites(context: Context, folders: List<FavoriteFolder>) {
        val arr = JSONArray()
        folders.forEach { f ->
            arr.put(
                JSONObject()
                    .put("id", f.id)
                    .put("label", f.label)
                    .put("treeUri", f.treeUri),
            )
        }
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_FAVORITES, arr.toString())
            .apply()
    }

    fun addFavorite(context: Context, treeUri: Uri, label: String): List<FavoriteFolder> {
        val uri = treeUri.toString()
        val current = loadFavorites(context).toMutableList()
        if (current.any { it.treeUri == uri }) return current
        current.add(
            FavoriteFolder(
                id = uri,
                label = label.ifBlank { treeUri.lastPathSegment ?: "Folder" },
                treeUri = uri,
            ),
        )
        saveFavorites(context, current)
        return current
    }

    fun removeFavorite(context: Context, id: String): List<FavoriteFolder> {
        val next = loadFavorites(context).filterNot { it.id == id }
        saveFavorites(context, next)
        return next
    }
}
