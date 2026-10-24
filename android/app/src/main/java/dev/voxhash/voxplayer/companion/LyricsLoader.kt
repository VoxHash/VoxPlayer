package dev.voxhash.voxplayer.companion

import android.content.ContentUris
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader

/**
 * On-device lyrics / timed text from sidecar files next to the media
 * (.lrc, .srt, .vtt, .txt). No cloud / no scraping.
 */
object LyricsLoader {
    data class Line(val timeMs: Long, val text: String)

    data class Lyrics(
        val sourceLabel: String,
        val timed: Boolean,
        val lines: List<Line>,
    ) {
        fun activeIndex(positionMs: Long): Int {
            if (lines.isEmpty()) return -1
            if (!timed) return 0
            var best = 0
            for (i in lines.indices) {
                if (lines[i].timeMs <= positionMs) best = i else break
            }
            return best
        }
    }

    private val SIDE_EXTS = listOf("lrc", "srt", "vtt", "txt")

    fun load(context: Context, mediaUri: Uri): Lyrics? {
        val text = readSidecar(context, mediaUri) ?: return null
        return parse(text.first, text.second)
    }

    fun parse(raw: String, sourceLabel: String): Lyrics? {
        val trimmed = raw.trim()
        if (trimmed.isEmpty()) return null
        val lower = sourceLabel.lowercase()
        return when {
            lower.endsWith(".lrc") || trimmed.contains(Regex("""\[\d{1,2}:\d{2}""")) ->
                parseLrc(trimmed, sourceLabel)
            lower.endsWith(".srt") || trimmed.contains(Regex("""^\d+\s*$""", RegexOption.MULTILINE)) ->
                parseSrt(trimmed, sourceLabel)
            lower.endsWith(".vtt") || trimmed.startsWith("WEBVTT") ->
                parseVtt(trimmed, sourceLabel)
            else ->
                Lyrics(
                    sourceLabel = sourceLabel,
                    timed = false,
                    lines = trimmed.lines().map { it.trim() }.filter { it.isNotEmpty() }
                        .map { Line(0L, it) },
                )
        }
    }

    private fun parseLrc(raw: String, label: String): Lyrics? {
        val re = Regex("""\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?](.*)$""")
        val out = ArrayList<Line>()
        raw.lineSequence().forEach { line ->
            val m = re.find(line.trim()) ?: return@forEach
            val min = m.groupValues[1].toLongOrNull() ?: return@forEach
            val sec = m.groupValues[2].toLongOrNull() ?: return@forEach
            val frac = m.groupValues[3]
            val ms = when {
                frac.isEmpty() -> 0L
                frac.length == 1 -> frac.toLong() * 100L
                frac.length == 2 -> frac.toLong() * 10L
                else -> frac.take(3).toLong()
            }
            val text = m.groupValues[4].trim()
            if (text.isEmpty()) return@forEach
            out.add(Line(min * 60_000L + sec * 1_000L + ms, text))
        }
        if (out.isEmpty()) {
            val plain = raw.lines().map { it.trim() }
                .filter { it.isNotEmpty() && !it.startsWith("[") }
                .map { Line(0L, it) }
            if (plain.isEmpty()) return null
            return Lyrics(label, timed = false, lines = plain)
        }
        return Lyrics(label, timed = true, lines = out.sortedBy { it.timeMs })
    }

    private fun parseSrt(raw: String, label: String): Lyrics? {
        val blocks = raw.replace("\r\n", "\n").split(Regex("""\n\s*\n"""))
        val out = ArrayList<Line>()
        val timeRe = Regex("""(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->""")
        for (block in blocks) {
            val lines = block.lines().map { it.trim() }.filter { it.isNotEmpty() }
            if (lines.isEmpty()) continue
            val timeLine = lines.firstOrNull { it.contains("-->") } ?: continue
            val m = timeRe.find(timeLine) ?: continue
            val ms = m.groupValues[1].toLong() * 3_600_000L +
                m.groupValues[2].toLong() * 60_000L +
                m.groupValues[3].toLong() * 1_000L +
                m.groupValues[4].toLong()
            val text = lines.dropWhile { !it.contains("-->") }.drop(1).joinToString(" ").trim()
            if (text.isNotEmpty()) out.add(Line(ms, text))
        }
        if (out.isEmpty()) return null
        return Lyrics(label, timed = true, lines = out.sortedBy { it.timeMs })
    }

    private fun parseVtt(raw: String, label: String): Lyrics? {
        val body = raw.replace("\r\n", "\n").removePrefix("WEBVTT").trim()
        val blocks = body.split(Regex("""\n\s*\n"""))
        val out = ArrayList<Line>()
        val timeRe = Regex("""(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->""")
        val timeReShort = Regex("""(\d{2}):(\d{2})\.(\d{3})\s*-->""")
        for (block in blocks) {
            val lines = block.lines().map { it.trim() }.filter { it.isNotEmpty() && !it.startsWith("NOTE") }
            if (lines.isEmpty()) continue
            val timeLine = lines.firstOrNull { it.contains("-->") } ?: continue
            val ms = timeRe.find(timeLine)?.let { m ->
                m.groupValues[1].toLong() * 3_600_000L +
                    m.groupValues[2].toLong() * 60_000L +
                    m.groupValues[3].toLong() * 1_000L +
                    m.groupValues[4].toLong()
            } ?: timeReShort.find(timeLine)?.let { m ->
                m.groupValues[1].toLong() * 60_000L +
                    m.groupValues[2].toLong() * 1_000L +
                    m.groupValues[3].toLong()
            } ?: continue
            val text = lines.dropWhile { !it.contains("-->") }.drop(1).joinToString(" ").trim()
            if (text.isNotEmpty()) out.add(Line(ms, text))
        }
        if (out.isEmpty()) return null
        return Lyrics(label, timed = true, lines = out.sortedBy { it.timeMs })
    }

    private fun readSidecar(context: Context, mediaUri: Uri): Pair<String, String>? {
        if (mediaUri.scheme == "file") {
            val f = File(mediaUri.path ?: return null)
            val base = f.nameWithoutExtension
            val parent = f.parentFile ?: return null
            for (ext in SIDE_EXTS) {
                val cand = File(parent, "$base.$ext")
                if (cand.isFile) {
                    return cand.readText(Charsets.UTF_8) to cand.name
                }
            }
            return null
        }
        // MediaStore / content: resolve DISPLAY_NAME + RELATIVE_PATH, then find sibling file.
        val meta = mediaStoreMeta(context, mediaUri) ?: return null
        for (ext in SIDE_EXTS) {
            val name = "${meta.baseName}.$ext"
            val sibling = findMediaStoreFile(context, meta.relativePath, name)
            if (sibling != null) {
                val text = readUriText(context, sibling) ?: continue
                return text to name
            }
            // Legacy DATA path sibling
            meta.dataPath?.let { data ->
                val parent = File(data).parentFile
                if (parent != null) {
                    val cand = File(parent, name)
                    if (cand.isFile) return cand.readText(Charsets.UTF_8) to name
                }
            }
        }
        return null
    }

    private data class MediaMeta(
        val baseName: String,
        val relativePath: String?,
        val dataPath: String?,
    )

    private fun mediaStoreMeta(context: Context, uri: Uri): MediaMeta? {
        val projection = mutableListOf(
            MediaStore.MediaColumns.DISPLAY_NAME,
        ).apply {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                add(MediaStore.MediaColumns.RELATIVE_PATH)
            }
            add(MediaStore.MediaColumns.DATA)
        }.toTypedArray()
        return try {
            context.contentResolver.query(uri, projection, null, null, null)?.use { c ->
                if (!c.moveToFirst()) return null
                val name = c.getString(c.getColumnIndexOrThrow(MediaStore.MediaColumns.DISPLAY_NAME))
                    ?: return null
                val base = name.substringBeforeLast('.', name)
                val relIdx = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    c.getColumnIndex(MediaStore.MediaColumns.RELATIVE_PATH)
                } else {
                    -1
                }
                val dataIdx = c.getColumnIndex(MediaStore.MediaColumns.DATA)
                MediaMeta(
                    baseName = base,
                    relativePath = if (relIdx >= 0) c.getString(relIdx) else null,
                    dataPath = if (dataIdx >= 0) c.getString(dataIdx) else null,
                )
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun findMediaStoreFile(context: Context, relativePath: String?, displayName: String): Uri? {
        val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL)
        } else {
            MediaStore.Files.getContentUri("external")
        }
        val projection = arrayOf(MediaStore.Files.FileColumns._ID, MediaStore.Files.FileColumns.DISPLAY_NAME)
        val (sel, args) = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && !relativePath.isNullOrBlank()) {
            "${MediaStore.Files.FileColumns.DISPLAY_NAME}=? AND ${MediaStore.MediaColumns.RELATIVE_PATH}=?" to
                arrayOf(displayName, relativePath)
        } else {
            "${MediaStore.Files.FileColumns.DISPLAY_NAME}=?" to arrayOf(displayName)
        }
        return try {
            context.contentResolver.query(collection, projection, sel, args, null)?.use { c ->
                if (!c.moveToFirst()) return null
                val id = c.getLong(c.getColumnIndexOrThrow(MediaStore.Files.FileColumns._ID))
                ContentUris.withAppendedId(collection, id)
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun readUriText(context: Context, uri: Uri): String? {
        return try {
            context.contentResolver.openInputStream(uri)?.use { input ->
                BufferedReader(InputStreamReader(input, Charsets.UTF_8)).readText()
            }
        } catch (_: Exception) {
            null
        }
    }
}
