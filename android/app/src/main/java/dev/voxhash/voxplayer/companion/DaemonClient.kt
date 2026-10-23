package dev.voxhash.voxplayer.companion

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * HTTP client for the VoxPlayer desktop control daemon (LAN / loopback).
 * No Google Play Services — plain OkHttp for GrapheneOS-friendly builds.
 */
class DaemonClient(
    baseUrl: String,
    private val http: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(3, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .build(),
) {
    private val root = baseUrl.trimEnd('/')
    private val jsonType = "application/json; charset=utf-8".toMediaType()

    data class Status(
        val playing: Boolean,
        val path: String,
        val positionMs: Long,
        val durationMs: Long,
        val volumePercent: Int,
        val version: String,
        val raw: JSONObject,
    )

    data class LibraryItem(
        val path: String,
        val title: String,
    )

    data class LibraryPage(
        val items: List<LibraryItem>,
        val total: Int,
        val limit: Int,
        val offset: Int,
    )

    fun status(): Status {
        val obj = getJson("/status")
        return Status(
            playing = obj.optBoolean("playing", false),
            path = obj.optString("path", ""),
            positionMs = obj.optLong("position_ms", 0L),
            durationMs = obj.optLong("duration_ms", 0L),
            volumePercent = obj.optInt("volume_percent", 0),
            version = obj.optString("version", ""),
            raw = obj,
        )
    }

    fun library(limit: Int = 200, offset: Int = 0): LibraryPage {
        val obj = getJson("/library?limit=$limit&offset=$offset")
        val arr: JSONArray = obj.optJSONArray("items") ?: JSONArray()
        val items = buildList {
            for (i in 0 until arr.length()) {
                val it = arr.optJSONObject(i) ?: continue
                val path = it.optString("path", "")
                if (path.isBlank()) continue
                add(
                    LibraryItem(
                        path = path,
                        title = it.optString("title", path.substringAfterLast('/')),
                    ),
                )
            }
        }
        return LibraryPage(
            items = items,
            total = obj.optInt("total", items.size),
            limit = obj.optInt("limit", limit),
            offset = obj.optInt("offset", offset),
        )
    }

    fun play() = postJson("/play")
    fun pause() = postJson("/pause")
    fun playPause() = postJson("/playpause")
    fun stop() = postJson("/stop")
    fun next() = postJson("/next")
    fun previous() = postJson("/previous")

    fun volume(percent: Int): JSONObject =
        postJson("/volume", JSONObject().put("percent", percent.coerceIn(0, 200)))

    fun seekRelative(ms: Long): JSONObject =
        postJson("/seek", JSONObject().put("relative_ms", ms))

    fun open(path: String): JSONObject =
        postJson("/open", JSONObject().put("path", path))

    private fun getJson(path: String): JSONObject {
        val req = Request.Builder().url(root + path).get().build()
        http.newCall(req).execute().use { resp ->
            val body = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) {
                throw IllegalStateException("HTTP ${resp.code}: $body")
            }
            return if (body.isBlank()) JSONObject() else JSONObject(body)
        }
    }

    private fun postJson(path: String, payload: JSONObject = JSONObject()): JSONObject {
        val req = Request.Builder()
            .url(root + path)
            .post(payload.toString().toRequestBody(jsonType))
            .build()
        http.newCall(req).execute().use { resp ->
            val body = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) {
                throw IllegalStateException("HTTP ${resp.code}: $body")
            }
            return if (body.isBlank()) JSONObject() else JSONObject(body)
        }
    }
}
