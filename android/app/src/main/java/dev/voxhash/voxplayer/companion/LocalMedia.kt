package dev.voxhash.voxplayer.companion

import android.content.ContentUris
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore

data class LocalMediaItem(
    val id: Long,
    val uri: Uri,
    val title: String,
    val artist: String,
    val album: String,
    val durationMs: Long,
    val isVideo: Boolean,
    /** MediaStore album id for AVRCP artwork URI (audio only; 0 if unknown). */
    val albumId: Long = 0L,
) {
    /** URI for MediaStore thumbnail / album art (offline, no cloud). */
    fun artworkContentUri(): Uri =
        if (!isVideo && albumId > 0L) {
            ContentUris.withAppendedId(
                Uri.parse("content://media/external/audio/albumart"),
                albumId,
            )
        } else {
            uri
        }
}

object LocalMediaStore {
    fun loadAudio(context: Context, limit: Int = 500): List<LocalMediaItem> {
        val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL)
        } else {
            MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
        }
        val projection = arrayOf(
            MediaStore.Audio.Media._ID,
            MediaStore.Audio.Media.TITLE,
            MediaStore.Audio.Media.ARTIST,
            MediaStore.Audio.Media.ALBUM,
            MediaStore.Audio.Media.DURATION,
            MediaStore.Audio.Media.ALBUM_ID,
        )
        val out = ArrayList<LocalMediaItem>()
        context.contentResolver.query(
            collection,
            projection,
            "${MediaStore.Audio.Media.IS_MUSIC}!=0",
            null,
            "${MediaStore.Audio.Media.DATE_ADDED} DESC",
        )?.use { c ->
            val idCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media._ID)
            val titleCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.TITLE)
            val artistCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.ARTIST)
            val albumCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.ALBUM)
            val durCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.DURATION)
            val albumIdCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.ALBUM_ID)
            while (c.moveToNext() && out.size < limit) {
                val id = c.getLong(idCol)
                out.add(
                    LocalMediaItem(
                        id = id,
                        uri = ContentUris.withAppendedId(collection, id),
                        title = c.getString(titleCol) ?: "Audio",
                        artist = c.getString(artistCol)?.takeIf { it.isNotBlank() && it != "<unknown>" } ?: "",
                        album = c.getString(albumCol)?.takeIf { it.isNotBlank() && it != "<unknown>" } ?: "",
                        durationMs = c.getLong(durCol).coerceAtLeast(0L),
                        isVideo = false,
                        albumId = c.getLong(albumIdCol).coerceAtLeast(0L),
                    ),
                )
            }
        }
        return out
    }

    fun loadVideo(context: Context, limit: Int = 300): List<LocalMediaItem> {
        val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL)
        } else {
            MediaStore.Video.Media.EXTERNAL_CONTENT_URI
        }
        // ARTIST / ALBUM on video are API 30+; query what exists and fill blanks on older devices.
        val projection = mutableListOf(
            MediaStore.Video.Media._ID,
            MediaStore.Video.Media.TITLE,
            MediaStore.Video.Media.DURATION,
        ).apply {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                add(MediaStore.Video.Media.ARTIST)
                add(MediaStore.Video.Media.ALBUM)
            }
        }.toTypedArray()
        val out = ArrayList<LocalMediaItem>()
        context.contentResolver.query(
            collection,
            projection,
            null,
            null,
            "${MediaStore.Video.Media.DATE_ADDED} DESC",
        )?.use { c ->
            val idCol = c.getColumnIndexOrThrow(MediaStore.Video.Media._ID)
            val titleCol = c.getColumnIndexOrThrow(MediaStore.Video.Media.TITLE)
            val artistCol = c.getColumnIndex(MediaStore.Video.Media.ARTIST)
            val albumCol = c.getColumnIndex(MediaStore.Video.Media.ALBUM)
            val durCol = c.getColumnIndexOrThrow(MediaStore.Video.Media.DURATION)
            while (c.moveToNext() && out.size < limit) {
                val id = c.getLong(idCol)
                out.add(
                    LocalMediaItem(
                        id = id,
                        uri = ContentUris.withAppendedId(collection, id),
                        title = c.getString(titleCol) ?: "Video",
                        artist = if (artistCol >= 0) {
                            c.getString(artistCol)?.takeIf { it.isNotBlank() && it != "<unknown>" } ?: ""
                        } else {
                            ""
                        },
                        album = if (albumCol >= 0) {
                            c.getString(albumCol)?.takeIf { it.isNotBlank() && it != "<unknown>" } ?: ""
                        } else {
                            ""
                        },
                        durationMs = c.getLong(durCol).coerceAtLeast(0L),
                        isVideo = true,
                    ),
                )
            }
        }
        return out
    }
}
