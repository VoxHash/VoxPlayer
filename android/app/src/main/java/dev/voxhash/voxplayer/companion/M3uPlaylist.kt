package dev.voxhash.voxplayer.companion

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.content.FileProvider
import java.io.File
import java.io.InputStream

/**
 * Offline M3U / M3U8 read-write for on-device queues and playlist folders.
 * No cloud sync — FileProvider share + SAF import only.
 */
object M3uPlaylist {
    data class Entry(
        val location: String,
        val title: String = "",
        val durationSec: Int = -1,
    )

    fun format(playlistName: String, entries: List<Entry>): String {
        val sb = StringBuilder()
        sb.appendLine("#EXTM3U")
        val name = playlistName.trim().ifBlank { "VoxPlayer" }
        sb.appendLine("#PLAYLIST:$name")
        entries.forEach { e ->
            val loc = e.location.trim()
            if (loc.isEmpty()) return@forEach
            val title = e.title.trim().ifBlank {
                Uri.parse(loc).lastPathSegment ?: "Track"
            }
            sb.appendLine("#EXTINF:${e.durationSec},$title")
            sb.appendLine(loc)
        }
        return sb.toString()
    }

    fun parse(text: String): Pair<String, List<Entry>> {
        var playlistName = "Imported"
        var pendingTitle = ""
        var pendingDur = -1
        val out = mutableListOf<Entry>()
        text.lineSequence().forEach { raw ->
            val line = raw.trim()
            if (line.isEmpty()) return@forEach
            when {
                line.startsWith("#EXTM3U", ignoreCase = true) -> Unit
                line.startsWith("#PLAYLIST:", ignoreCase = true) -> {
                    playlistName = line.substringAfter(':').trim().ifBlank { playlistName }
                }
                line.startsWith("#EXTINF:", ignoreCase = true) -> {
                    val body = line.substringAfter(':')
                    val comma = body.indexOf(',')
                    if (comma >= 0) {
                        pendingDur = body.substring(0, comma).trim().toIntOrNull() ?: -1
                        pendingTitle = body.substring(comma + 1).trim()
                    } else {
                        pendingDur = body.trim().toIntOrNull() ?: -1
                        pendingTitle = ""
                    }
                }
                line.startsWith("#") -> Unit
                else -> {
                    val loc = normalizeLocation(line) ?: return@forEach
                    out.add(
                        Entry(
                            location = loc,
                            title = pendingTitle.ifBlank {
                                Uri.parse(loc).lastPathSegment ?: "Track"
                            },
                            durationSec = pendingDur,
                        ),
                    )
                    pendingTitle = ""
                    pendingDur = -1
                }
            }
        }
        return playlistName.take(64) to out
    }

    fun parse(stream: InputStream): Pair<String, List<Entry>> =
        parse(stream.bufferedReader().use { it.readText() })

    /**
     * Map M3U locations onto local library URIs when possible (exact URI,
     * then last-path-segment match). Unmatched content/file URIs are kept.
     */
    fun resolveToTracks(
        entries: List<Entry>,
        localItems: List<LocalMediaItem>,
    ): List<LocalPlaylistStore.Track> {
        val byUri = localItems.associateBy { it.uri.toString() }
        val byName = localItems.groupBy {
            it.uri.lastPathSegment?.lowercase().orEmpty()
        }
        return entries.mapNotNull { e ->
            val loc = e.location.trim()
            if (loc.isEmpty()) return@mapNotNull null
            val hit = byUri[loc]
                ?: run {
                    val name = Uri.parse(loc).lastPathSegment?.lowercase().orEmpty()
                    if (name.isEmpty()) null else byName[name]?.firstOrNull()
                }
            if (hit != null) {
                LocalPlaylistStore.Track(
                    uri = hit.uri.toString(),
                    title = hit.title.ifBlank { e.title },
                    artist = hit.artist,
                    album = hit.album,
                    isVideo = hit.isVideo,
                )
            } else if (loc.startsWith("content:", ignoreCase = true) ||
                loc.startsWith("file:", ignoreCase = true)
            ) {
                LocalPlaylistStore.Track(
                    uri = loc,
                    title = e.title.ifBlank { Uri.parse(loc).lastPathSegment ?: "Track" },
                    artist = "",
                    album = "",
                    isVideo = loc.lowercase().let {
                        it.endsWith(".mp4") || it.endsWith(".mkv") || it.endsWith(".webm")
                    },
                )
            } else {
                null
            }
        }.distinctBy { it.uri }.take(500)
    }

    fun writeCacheFile(context: Context, playlistName: String, entries: List<Entry>): File {
        val dir = File(context.cacheDir, "share").also { it.mkdirs() }
        val safe = playlistName.replace(Regex("[^A-Za-z0-9._-]"), "_").take(40).ifBlank { "playlist" }
        val out = File(dir, "${safe}_${System.currentTimeMillis()}.m3u")
        out.writeText(format(playlistName, entries), Charsets.UTF_8)
        return out
    }

    fun shareIntent(context: Context, file: File, playlistName: String): Intent {
        val contentUri = FileProvider.getUriForFile(
            context,
            NowPlayingShare.authority(context),
            file,
        )
        return Intent(Intent.ACTION_SEND).apply {
            type = "audio/x-mpegurl"
            putExtra(Intent.EXTRA_STREAM, contentUri)
            putExtra(Intent.EXTRA_SUBJECT, playlistName.ifBlank { "VoxPlayer playlist" })
            putExtra(Intent.EXTRA_TEXT, "VoxPlayer M3U (offline)")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            clipData = android.content.ClipData.newUri(
                context.contentResolver,
                "m3u",
                contentUri,
            )
        }.let { Intent.createChooser(it, "Export M3U") }
    }

    private fun normalizeLocation(line: String): String? {
        val t = line.trim()
        if (t.isEmpty()) return null
        if (t.startsWith("http:", ignoreCase = true) || t.startsWith("https:", ignoreCase = true)) {
            return null // offline companion — skip remote streams
        }
        if (t.startsWith("content:", ignoreCase = true) || t.startsWith("file:", ignoreCase = true)) {
            return t
        }
        if (t.startsWith("/")) {
            return Uri.fromFile(File(t)).toString()
        }
        return t
    }
}
