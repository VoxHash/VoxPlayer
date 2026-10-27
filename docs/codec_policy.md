# Codec policy (standing — ROADMAP #82)

**Non-goal:** VoxPlayer does **not** invent or vendor greenfield **H.264 / x264 / H.265 / x265** (or equivalent in-tree encoder/decoder source trees).

**Do:** wrap maintained FOSS and platform stacks:

| Surface | Allowed decode path |
|---------|---------------------|
| Desktop | System/bundled **libvlc** plugins and/or linked **libav** (PyAV → libavcodec / dav1d / libopus, …) |
| Android / Quest / GrapheneOS | **Media3 → MediaCodec** (AOSP / device firmware) |

**Do not:**

- Copy VideoLAN x264, MultiCoreWare x265, Cisco OpenH264, or similar **source trees** into this repository under `native/`, `third_party/`, `vendor/`, `codecs/`, etc.
- Claim a Vox-authored H.264/H.265 bitstream codec as a product feature
- Reintroduce `python-vlc` as the decode API (binding ≠ decode; see independence matrix)

**Allowed (not a policy violation):**

- Calling **system / distro** FOSS libraries already installed (e.g. PyAV using host `libx264` / `libx265` / `libsvtav1` / `libopus` **only** to generate tiny test fixtures, or libav to decode)
- Shipping **prebuilt** libvlc plugin trees under `native_core/` that were staged from the host (LGPL/GPL inventory remains the packager’s duty)
- Documenting and probing capability (Help → Codec support… / Codec policy…)

## Enforcement

```bash
.venv/bin/python scripts/e2e_codec_policy.py
# also run from e2e_smoke / CI via independence + codec_policy gates
```

Canonical machine text: `voxplayer.engine.codec_policy`.

## Related

- `docs/codec_fixture_matrix.md` — H.264 / HEVC / AV1 / Opus fixtures
- `docs/independence_matrix.md` — VLC / ffmpeg CLI removal outcomes
