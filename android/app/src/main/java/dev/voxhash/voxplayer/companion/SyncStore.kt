package dev.voxhash.voxplayer.companion

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Local cache of playlists / podcast feeds pulled from the desktop daemon
 * (Wi‑Fi HTTP or Bluetooth RFCOMM). No cloud account.
 */
class SyncStore(context: Context) {
    private val dir = File(context.filesDir, "sync").also { it.mkdirs() }
    private val playlistsFile = File(dir, "playlists.json")
    private val podcastsFile = File(dir, "podcasts.json")

    data class SyncedPlaylist(
        val name: String,
        val items: List<DaemonClient.LibraryItem>,
    )

    data class SyncedEpisode(
        val title: String,
        val guid: String,
        val enclosureUrl: String,
        val localPath: String,
    )

    data class SyncedFeed(
        val url: String,
        val title: String,
        val episodes: List<SyncedEpisode>,
    )

    fun savePlaylists(playlists: List<DaemonClient.PlaylistExport>) {
        val arr = JSONArray()
        playlists.forEach { pl ->
            val items = JSONArray()
            pl.items.forEach { it ->
                items.put(JSONObject().put("path", it.path).put("title", it.title))
            }
            arr.put(JSONObject().put("name", pl.name).put("items", items))
        }
        playlistsFile.writeText(JSONObject().put("playlists", arr).toString())
    }

    fun loadPlaylists(): List<SyncedPlaylist> {
        if (!playlistsFile.isFile) return emptyList()
        return try {
            val arr = JSONObject(playlistsFile.readText()).optJSONArray("playlists") ?: JSONArray()
            buildList {
                for (i in 0 until arr.length()) {
                    val pl = arr.optJSONObject(i) ?: continue
                    val itemsArr = pl.optJSONArray("items") ?: JSONArray()
                    val items = buildList {
                        for (j in 0 until itemsArr.length()) {
                            val it = itemsArr.optJSONObject(j) ?: continue
                            val path = it.optString("path", "")
                            if (path.isBlank()) continue
                            add(
                                DaemonClient.LibraryItem(
                                    path,
                                    it.optString("title", path.substringAfterLast('/')),
                                ),
                            )
                        }
                    }
                    add(SyncedPlaylist(pl.optString("name", "Playlist"), items))
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun savePodcasts(feeds: List<DaemonClient.PodcastFeedExport>) {
        val arr = JSONArray()
        feeds.forEach { f ->
            val eps = JSONArray()
            f.episodes.forEach { e ->
                eps.put(
                    JSONObject()
                        .put("title", e.title)
                        .put("guid", e.guid)
                        .put("enclosure_url", e.enclosureUrl)
                        .put("local_path", e.localPath),
                )
            }
            arr.put(
                JSONObject()
                    .put("url", f.url)
                    .put("title", f.title)
                    .put("episodes", eps),
            )
        }
        podcastsFile.writeText(JSONObject().put("feeds", arr).toString())
    }

    fun loadPodcasts(): List<SyncedFeed> {
        if (!podcastsFile.isFile) return emptyList()
        return try {
            val arr = JSONObject(podcastsFile.readText()).optJSONArray("feeds") ?: JSONArray()
            buildList {
                for (i in 0 until arr.length()) {
                    val f = arr.optJSONObject(i) ?: continue
                    val eps = f.optJSONArray("episodes") ?: JSONArray()
                    val episodes = buildList {
                        for (j in 0 until eps.length()) {
                            val e = eps.optJSONObject(j) ?: continue
                            add(
                                SyncedEpisode(
                                    title = e.optString("title", "Episode"),
                                    guid = e.optString("guid", ""),
                                    enclosureUrl = e.optString("enclosure_url", ""),
                                    localPath = e.optString("local_path", ""),
                                ),
                            )
                        }
                    }
                    add(
                        SyncedFeed(
                            url = f.optString("url", ""),
                            title = f.optString("title", "Feed"),
                            episodes = episodes,
                        ),
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    companion object {
        fun playlistsFromJson(obj: JSONObject): List<DaemonClient.PlaylistExport> {
            val arr = obj.optJSONArray("playlists") ?: JSONArray()
            return buildList {
                for (i in 0 until arr.length()) {
                    val pl = arr.optJSONObject(i) ?: continue
                    val itemsArr = pl.optJSONArray("items") ?: JSONArray()
                    val items = buildList {
                        for (j in 0 until itemsArr.length()) {
                            val it = itemsArr.optJSONObject(j) ?: continue
                            val path = it.optString("path", "")
                            if (path.isBlank()) continue
                            add(
                                DaemonClient.LibraryItem(
                                    path,
                                    it.optString("title", path.substringAfterLast('/')),
                                ),
                            )
                        }
                    }
                    add(DaemonClient.PlaylistExport(pl.optString("name", "Playlist"), items))
                }
            }
        }

        fun podcastsFromJson(obj: JSONObject): List<DaemonClient.PodcastFeedExport> {
            val arr = obj.optJSONArray("feeds") ?: JSONArray()
            return buildList {
                for (i in 0 until arr.length()) {
                    val f = arr.optJSONObject(i) ?: continue
                    val eps = f.optJSONArray("episodes") ?: JSONArray()
                    val episodes = buildList {
                        for (j in 0 until eps.length()) {
                            val e = eps.optJSONObject(j) ?: continue
                            add(
                                DaemonClient.PodcastEpisode(
                                    title = e.optString("title", "Episode"),
                                    guid = e.optString("guid", ""),
                                    enclosureUrl = e.optString("enclosure_url", ""),
                                    localPath = e.optString("local_path", ""),
                                ),
                            )
                        }
                    }
                    add(
                        DaemonClient.PodcastFeedExport(
                            url = f.optString("url", ""),
                            title = f.optString("title", "Feed"),
                            episodes = episodes,
                        ),
                    )
                }
            }
        }
    }
}
