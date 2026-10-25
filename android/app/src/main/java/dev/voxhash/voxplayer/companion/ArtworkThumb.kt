package dev.voxhash.voxplayer.companion

import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.util.Size
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LibraryMusic
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Offline MediaStore / content thumbnail (album art or video frame). No network.
 */
@Composable
fun ArtworkThumb(
    contentUri: Uri,
    isVideo: Boolean,
    modifier: Modifier = Modifier,
    sizePx: Int = 256,
) {
    val context = LocalContext.current
    var bitmap by remember(contentUri) { mutableStateOf<Bitmap?>(null) }

    LaunchedEffect(contentUri, sizePx) {
        bitmap = withContext(Dispatchers.IO) {
            loadLocalThumb(context, contentUri, sizePx)
        }
    }

    Box(
        modifier.background(VoxColors.BgPanel),
        contentAlignment = Alignment.Center,
    ) {
        val bmp = bitmap
        if (bmp != null) {
            Image(
                bitmap = bmp.asImageBitmap(),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize(),
            )
        } else {
            Icon(
                if (isVideo) Icons.Default.PlayArrow else Icons.Default.LibraryMusic,
                contentDescription = null,
                tint = VoxColors.Accent,
                modifier = Modifier.size(36.dp),
            )
        }
    }
}

private fun loadLocalThumb(
    context: android.content.Context,
    uri: Uri,
    sizePx: Int,
): Bitmap? {
    return try {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            context.contentResolver.loadThumbnail(uri, Size(sizePx, sizePx), null)
        } else {
            @Suppress("DEPRECATION")
            android.provider.MediaStore.Images.Media.getBitmap(context.contentResolver, uri)
        }
    } catch (_: Exception) {
        // Album-art URI may fail; try nothing — caller shows placeholder icon.
        null
    }
}
