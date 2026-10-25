package dev.voxhash.voxplayer.companion

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.util.Size
import androidx.core.content.FileProvider
import java.io.File
import java.io.FileOutputStream

/**
 * Offline now-playing share card — PNG written to app cache, shared via
 * the system chooser (no cloud upload / no GMS).
 */
object NowPlayingShare {
    private const val AUTHORITY_SUFFIX = ".share"

    fun authority(context: Context): String =
        context.packageName + AUTHORITY_SUFFIX

    fun shareCard(
        context: Context,
        title: String,
        artist: String,
        album: String,
        artworkUri: Uri?,
    ): Intent {
        val bmp = renderCard(context, title, artist, album, artworkUri)
        val dir = File(context.cacheDir, "share").also { it.mkdirs() }
        val out = File(dir, "now_playing_${System.currentTimeMillis()}.png")
        FileOutputStream(out).use { fos ->
            bmp.compress(Bitmap.CompressFormat.PNG, 100, fos)
        }
        bmp.recycle()
        val contentUri = FileProvider.getUriForFile(context, authority(context), out)
        val text = buildString {
            append(title.ifBlank { "VoxPlayer" })
            if (artist.isNotBlank()) append(" — ").append(artist)
            if (album.isNotBlank()) append(" · ").append(album)
            append("\nvia VoxPlayer (offline)")
        }
        return Intent(Intent.ACTION_SEND).apply {
            type = "image/png"
            putExtra(Intent.EXTRA_STREAM, contentUri)
            putExtra(Intent.EXTRA_TEXT, text)
            putExtra(Intent.EXTRA_SUBJECT, title.ifBlank { "Now playing" })
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            clipData = android.content.ClipData.newUri(
                context.contentResolver,
                "now_playing",
                contentUri,
            )
        }.let { Intent.createChooser(it, "Share now playing") }
    }

    private fun renderCard(
        context: Context,
        title: String,
        artist: String,
        album: String,
        artworkUri: Uri?,
    ): Bitmap {
        val w = 1080
        val h = 1080
        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        canvas.drawColor(Color.parseColor("#0B0F14"))

        val artSize = 640
        val artLeft = ((w - artSize) / 2).toFloat()
        val artTop = 120f
        val artRect = RectF(artLeft, artTop, artLeft + artSize, artTop + artSize)
        val artPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#151C26")
        }
        canvas.drawRoundRect(artRect, 28f, 28f, artPaint)

        val thumb = loadArt(context, artworkUri, artSize)
        if (thumb != null) {
            val src = android.graphics.Rect(0, 0, thumb.width, thumb.height)
            canvas.drawBitmap(thumb, src, artRect, Paint(Paint.FILTER_BITMAP_FLAG))
            thumb.recycle()
        } else {
            val label = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.parseColor("#FF8A3D")
                textAlign = Paint.Align.CENTER
                textSize = 64f
                typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            }
            canvas.drawText("VoxPlayer", w / 2f, artTop + artSize / 2f + 20f, label)
        }

        val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE
            textAlign = Paint.Align.CENTER
            textSize = 56f
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        }
        val subPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#9AA4B2")
            textAlign = Paint.Align.CENTER
            textSize = 36f
        }
        val accentPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#FF8A3D")
            textAlign = Paint.Align.CENTER
            textSize = 28f
        }
        var y = artTop + artSize + 90f
        canvas.drawText(ellipsize(title.ifBlank { "(nothing loaded)" }, titlePaint, w - 120f), w / 2f, y, titlePaint)
        y += 56f
        if (artist.isNotBlank()) {
            canvas.drawText(ellipsize(artist, subPaint, w - 120f), w / 2f, y, subPaint)
            y += 48f
        }
        if (album.isNotBlank()) {
            canvas.drawText(ellipsize(album, subPaint, w - 120f), w / 2f, y, subPaint)
            y += 48f
        }
        canvas.drawText("VoxPlayer · offline share", w / 2f, h - 64f, accentPaint)
        return bmp
    }

    private fun loadArt(context: Context, uri: Uri?, size: Int): Bitmap? {
        if (uri == null) return null
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                context.contentResolver.loadThumbnail(uri, Size(size, size), null)
            } else {
                @Suppress("DEPRECATION")
                android.provider.MediaStore.Images.Media.getBitmap(context.contentResolver, uri)
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun ellipsize(text: String, paint: Paint, maxWidth: Float): String {
        if (paint.measureText(text) <= maxWidth) return text
        var end = text.length
        while (end > 1 && paint.measureText(text.take(end) + "…") > maxWidth) end--
        return text.take(end) + "…"
    }
}
