package dev.voxhash.voxplayer.companion

import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import android.util.Log
import com.yinnho.upnpcast.DLNACast
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

/**
 * Opt-in DLNA / UPnP casting to LAN MediaRenderers — no Google Cast SDK / GMS.
 * Backed by MIT [UPnPCast](https://github.com/yinnho/UPnPCast).
 */
object DlnaCastControl {
    const val PREFS = "voxplayer_dlna"
    const val KEY_ENABLED = "enabled"

    data class Renderer(
        val id: String,
        val name: String,
        val address: String,
        val isTv: Boolean,
    )

    fun loadEnabled(context: Context): Boolean =
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean(KEY_ENABLED, false)

    fun saveEnabled(context: Context, enabled: Boolean) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_ENABLED, enabled)
            .apply()
    }

    @Volatile
    private var initialized = false

    fun ensureInit(context: Context) {
        if (initialized) return
        synchronized(this) {
            if (initialized) return
            DLNACast.init(context.applicationContext)
            initialized = true
            Log.i(TAG, "DLNACast initialized (no GMS Cast)")
        }
    }

    fun cleanup() {
        if (!initialized) return
        try {
            DLNACast.cleanup()
        } catch (e: Exception) {
            Log.w(TAG, "DLNACast.cleanup", e)
        }
        initialized = false
    }

    suspend fun search(context: Context, timeoutMs: Long = 5_000L): List<Renderer> =
        withContext(Dispatchers.IO) {
            ensureInit(context)
            DLNACast.search(timeout = timeoutMs).map {
                Renderer(
                    id = it.id,
                    name = it.name.ifBlank { it.address },
                    address = it.address,
                    isTv = it.isTV,
                )
            }
        }

    /**
     * Cast [uri] to [deviceId]. Resolves MediaStore / content URIs to a local
     * cache file when needed so the built-in HTTP file server can stream.
     */
    suspend fun castUri(
        context: Context,
        deviceId: String,
        uri: Uri,
        title: String,
        mimeHint: String = "",
    ): String = withContext(Dispatchers.IO) {
        ensureInit(context)
        val device = DLNACast.search(timeout = 2_500).find { it.id == deviceId }
            ?: error("Renderer not found — scan again")
        val path = resolveLocalPath(context, uri)
            ?: materializeToCache(context, uri, title, mimeHint)
        DLNACast.castLocalFile(path, device, title.ifBlank { File(path).name })
        "Casting to ${device.name}"
    }

    suspend fun pause(): Boolean = withContext(Dispatchers.IO) {
        if (!initialized) return@withContext false
        DLNACast.pause()
    }

    suspend fun play(): Boolean = withContext(Dispatchers.IO) {
        if (!initialized) return@withContext false
        DLNACast.play()
    }

    suspend fun stop(): Boolean = withContext(Dispatchers.IO) {
        if (!initialized) return@withContext false
        DLNACast.stop()
    }

    private fun resolveLocalPath(context: Context, uri: Uri): String? {
        if (uri.scheme == "file") {
            val p = uri.path ?: return null
            return if (File(p).isFile) p else null
        }
        if (uri.scheme != "content") return null
        // Legacy DATA column — often blank on Q+ / GrapheneOS Storage Scopes.
        val projection = arrayOf(MediaStore.MediaColumns.DATA)
        return try {
            context.contentResolver.query(uri, projection, null, null, null)?.use { c ->
                if (!c.moveToFirst()) return null
                val idx = c.getColumnIndex(MediaStore.MediaColumns.DATA)
                if (idx < 0) return null
                c.getString(idx)?.takeIf { it.isNotBlank() && File(it).isFile }
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun materializeToCache(
        context: Context,
        uri: Uri,
        title: String,
        mimeHint: String,
    ): String {
        val mime = mimeHint.ifBlank {
            context.contentResolver.getType(uri).orEmpty()
        }
        val ext = when {
            mime.startsWith("audio/") -> mime.substringAfter('/').substringBefore('+').ifBlank { "mp3" }
            mime.startsWith("video/") -> mime.substringAfter('/').substringBefore('+').ifBlank { "mp4" }
            else -> uri.lastPathSegment?.substringAfterLast('.', "")?.takeIf { it.length in 2..5 } ?: "bin"
        }
        val safe = title.replace(Regex("[^A-Za-z0-9._-]"), "_").take(48).ifBlank { "cast" }
        val dir = File(context.cacheDir, "dlna_cast").also { it.mkdirs() }
        val out = File(dir, "$safe.$ext")
        context.contentResolver.openInputStream(uri)?.use { input ->
            FileOutputStream(out).use { output -> input.copyTo(output) }
        } ?: error("Cannot read media for cast")
        if (Build.VERSION.SDK_INT >= 26) {
            // Keep cache bounded
            dir.listFiles()
                ?.filter { it.isFile && it != out }
                ?.sortedByDescending { it.lastModified() }
                ?.drop(4)
                ?.forEach { it.delete() }
        }
        return out.absolutePath
    }

    private const val TAG = "VoxDlnaCast"
}
