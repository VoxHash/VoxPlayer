# Codec fixture matrix

Automated **H.264 / H.265 (HEVC) / AV1 / Opus** decode coverage for Phase 7.

**Policy:** wrap maintained FOSS + platform MediaCodec — **do not** invent in-tree x264/x265. Canonical: [`codec_policy.md`](codec_policy.md) (CI-enforced).

## Desktop (FOSS libav)

| Codec | Fixture | How |
|-------|---------|-----|
| H.264 | `fixtures/codecs/fixture_h264.mp4` | Encode via PyAV (`libx264`) → decode via linked libav |
| HEVC | `fixtures/codecs/fixture_hevc.mp4` | Encode via `libx265` when present → decode |
| AV1 | `fixtures/codecs/fixture_av1.mp4` | Encode via `libsvtav1` / `libaom-av1` when present → decode (`dav1d`) |
| Opus | `fixtures/codecs/fixture_opus.ogg` | Encode via `libopus` → decode |

```bash
pip install "voxplayer[libav]"
.venv/bin/python scripts/generate_codec_fixtures.py
.venv/bin/python scripts/e2e_codec_fixtures.py
# or Help → Codec support… in the desktop app
```

- **Required for CI pass:** H.264 + Opus encode+decode when PyAV is installed.
- **Soft-skip:** HEVC / AV1 if the host has no FOSS encoder (decode still tested when encode succeeds).

## Android / Quest (Media3 → MediaCodec)

Per-device probe — GrapheneOS-honest:

| Codec | MIME | Expectation |
|-------|------|-------------|
| H.264 | `video/avc` | Decoder present on phone/tablet AOSP API 26+ |
| HEVC | `video/hevc` | Common; optional on some Quest / OEM panels |
| AV1 | `video/av01` | Often API 10+/14+ on phones; **may be absent on Quest** |
| Opus | `audio/opus` | Decode from API 21+ |

In the companion: **More → Codec fixture matrix** (`CodecFixtureMatrix.probe()`).

Missing AV1/HEVC on a given device is a **platform limit**, not a VoxPlayer regression.

## Related

- `docs/independence_matrix.md` — VLC / ffmpeg CLI removal outcomes
- ROADMAP #81 / #82 — fixture matrix + standing codec policy (`e2e_codec_policy.py`)
