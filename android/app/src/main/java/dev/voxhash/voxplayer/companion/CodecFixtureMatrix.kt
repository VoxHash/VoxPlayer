package dev.voxhash.voxplayer.companion

import android.media.MediaCodecList
import android.media.MediaFormat
import android.os.Build

/**
 * GrapheneOS-honest codec fixture matrix for Android / Quest (Media3 → MediaCodec).
 *
 * Desktop generates tiny H.264 / HEVC / AV1 / Opus samples via FOSS libav (PyAV).
 * On device we cannot ship those binaries as a decode guarantee — support is
 * **per-device** via [MediaCodecList]. This probe reports what MediaCodec can
 * decode; Media3 ExoPlayer uses the same platform decoders.
 *
 * Policy: wrap platform MediaCodec / FOSS — do not invent in-tree x264/x265.
 */
object CodecFixtureMatrix {

    data class CodecRow(
        val id: String,
        val mime: String,
        val label: String,
        val decoderFound: Boolean,
        val decoderName: String?,
        val notes: String,
    )

    data class Report(
        val sdk: Int,
        val device: String,
        val rows: List<CodecRow>,
    ) {
        fun summaryLines(): List<String> {
            val lines = mutableListOf(
                "Codec fixture matrix (Android / Quest — MediaCodec)",
                "Device: $device  API $sdk",
                "",
                "Honest limits: support is device/firmware-specific. GrapheneOS",
                "follows AOSP MediaCodec; Quest / OEM builds may omit AV1 or HEVC.",
                "Media3 uses these platform decoders (no GMS).",
                "Policy: wrap MediaCodec — do not invent in-tree x264/x265.",
                "",
            )
            for (row in rows) {
                val status = if (row.decoderFound) "PASS" else "MISS"
                val who = row.decoderName ?: "(none)"
                lines += "  [$status] ${row.label}  mime=${row.mime}  decoder=$who"
                if (row.notes.isNotBlank()) {
                    lines += "         ${row.notes}"
                }
            }
            return lines
        }

        fun asText(): String = summaryLines().joinToString("\n")
    }

    private val focus = listOf(
        Triple("h264", MediaFormat.MIMETYPE_VIDEO_AVC, "H.264 / AVC"),
        Triple("hevc", MediaFormat.MIMETYPE_VIDEO_HEVC, "H.265 / HEVC"),
        Triple("av1", "video/av01", "AV1"),
        Triple("opus", MediaFormat.MIMETYPE_AUDIO_OPUS, "Opus"),
    )

    fun probe(): Report {
        val list = MediaCodecList(MediaCodecList.REGULAR_CODECS)
        val rows = focus.map { (id, mime, label) ->
            val format = buildProbeFormat(mime)
            val name = try {
                list.findDecoderForFormat(format)
            } catch (_: IllegalArgumentException) {
                null
            } catch (_: IllegalStateException) {
                null
            }
            CodecRow(
                id = id,
                mime = mime,
                label = label,
                decoderFound = !name.isNullOrBlank(),
                decoderName = name,
                notes = notesFor(id, !name.isNullOrBlank()),
            )
        }
        val device = buildString {
            append(Build.MANUFACTURER)
            append(' ')
            append(Build.MODEL)
        }.trim()
        return Report(sdk = Build.VERSION.SDK_INT, device = device, rows = rows)
    }

    private fun buildProbeFormat(mime: String): MediaFormat {
        if (mime.startsWith("audio/")) {
            return MediaFormat.createAudioFormat(mime, 48_000, 1)
        }
        val format = MediaFormat.createVideoFormat(mime, 64, 48)
        // Lollipop quirk: clear frame rate for findDecoderForFormat
        if (Build.VERSION.SDK_INT == Build.VERSION_CODES.LOLLIPOP) {
            format.setString(MediaFormat.KEY_FRAME_RATE, null)
        }
        return format
    }

    private fun notesFor(id: String, found: Boolean): String = when (id) {
        "h264" -> if (found) "Baseline/Main expected on API 26+" else "Unexpected — AVC is mandatory on phone/tablet AOSP"
        "hevc" -> if (found) "Main Profile typical from API 21+" else "Optional on some devices / Quest panels"
        "av1" -> if (found) {
            "Present (often API 10+/14+ mandatory on phones)"
        } else {
            "Often missing on Quest / older GrapheneOS builds — not a VoxPlayer bug"
        }
        "opus" -> if (found) "Decode from API 21+; encode from API 29+" else "Unexpected on API 26+"
        else -> ""
    }
}
