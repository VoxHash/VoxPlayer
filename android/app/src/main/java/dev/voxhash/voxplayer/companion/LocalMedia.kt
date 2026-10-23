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
    val durationMs: Long,
    val isVideo: Boolean,
)

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
            MediaStore.Audio.Media.DURATION,
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
            val durCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.DURATION)
            while (c.moveToNext() && out.size < limit) {
                val id = c.getLong(idCol)
                out.add(
                    LocalMediaItem(
                        id = id,
                        uri = ContentUris.withAppendedId(collection, id),
                        title = c.getString(titleCol) ?: "Audio",
                        artist = c.getString(artistCol) ?: "",
                        durationMs = c.getLong(durCol).coerceAtLeast(0L),
                        isVideo = false,
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
        val projection = arrayOf(
            MediaStore.Video.Media._ID,
            MediaStore.Video.Media.TITLE,
            MediaStore.Video.Media.ARTIST,
            MediaStore.Video.Media.DURATION,
        )
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
            val artistCol = c.getColumnIndexOrThrow(MediaStore.Video.Media.ARTIST)
            val durCol = c.getColumnIndexOrThrow(MediaStore.Video.Media.DURATION)
            while (c.moveToNext() && out.size < limit) {
                val id = c.getLong(idCol)
                out.add(
                    LocalMediaItem(
                        id = id,
                        uri = ContentUris.withAppendedId(collection, id),
                        title = c.getString(titleCol) ?: "Video",
                        artist = c.getString(artistCol) ?: "",
                        durationMs = c.getLong(durCol).coerceAtLeast(0L),
                        isVideo = true,
                    ),
                )
            }
        }
        return out
    }
}
