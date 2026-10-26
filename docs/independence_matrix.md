# Dependency independence matrix

Honest status after **1.99.0** (Vox `libvlc_ffi`) and **1.100.0** (this matrix + e2e gates).

**Binding ≠ decode.** Removing `python-vlc` did not remove libvlc. Desktop playback still demuxes/decodes through **system or bundled libvlc plugins**.

## Live probe

```bash
.venv/bin/python scripts/independence_matrix.py
# or Help → Dependency independence… in the desktop app
```

## Matrix

| Surface | Capability | Today | If system VLC / libvlc removed | If ffmpeg/ffprobe CLI removed | FOSS target |
|---------|------------|-------|--------------------------------|-------------------------------|-------------|
| **Desktop** | A/V decode, volume 0–200, WID embed | libvlc via `libvlc_ffi` | **Hard fail** without a complete `native_core/` bundle | Playback OK | Phase 7: bundled libavcodec + demux + HW; retire system VLC |
| **Desktop** | python-vlc | **Absent** (1.99.0) | N/A | N/A | Keep absent |
| **Desktop** | Scan / meta / thumbs / spectrum | `vox_scan` + ffmpeg CLI / `vox_meta` | Unaffected | Meta/thumbs/viz degrade | Linked libav in workers |
| **Android / GrapheneOS** | On-device A/V | Media3 → MediaCodec | Unaffected (never used VLC) | Unaffected | Stay Media3; no GMS |
| **Quest** | 2D panel | Same Media3 companion | Unaffected | Unaffected | Same; honest PiP/panel limits |
| **Codecs H.264 / H.265 / AV1 / Opus** | Decode | Desktop: VLC plugins; Android: MediaCodec | Desktop fails without replacement | Probe only | **Wrap FOSS** (libav, dav1d, MediaCodec) — **do not invent** in-tree x264/x265 |

## This machine (dev profile)

Typical Arch/Manjaro workspace with `pacman -S vlc` and no staged `native_core/`:

| Action | Result |
|--------|--------|
| Uninstall `python-vlc` | **OK** — already the supported state |
| `pacman -Rns vlc` (no bundle) | Desktop **will not start** (`run.py` preflight / `NativeEngineError`) |
| Remove `ffmpeg` only | Playback continues; thumbnails / Help codec probe / spectrum degrade |
| Android/Quest APK | Unrelated — Media3 only |

## Codec policy (opsec-aligned)

- **Do not** ship greenfield H.264 / x264 / H.265 / x265 implementations in-tree.
- **Do** wrap maintained FOSS decoders and platform MediaCodec; document LGPL/GPL plugin license inventory when bundling.
- Encoders (x264/x265) are out of scope until a product encode/export feature exists; the player needs **decoders**.

## Phase 7 (ROADMAP)

See ROADMAP items **76+** for staged work: matrix (done), complete native_core CI, parallel libav backend, retire system VLC, meta off CLI, Android codec fixture matrix.
