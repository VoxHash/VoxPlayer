# Dependency independence matrix

Honest status after **1.99.0** (Vox `libvlc_ffi`), **1.100.0** (matrix + e2e gates), and **1.101.0** (stageable `native_core/` + bundle isolation e2e).

**Binding ≠ decode.** Removing `python-vlc` did not remove libvlc. Desktop playback still demuxes/decodes through **system or bundled libvlc plugins**.

## Live probe

```bash
.venv/bin/python scripts/independence_matrix.py
.venv/bin/python packaging/stage_native_core.py --force
.venv/bin/python scripts/e2e_native_core_bundle.py   # load libvlc from staged tree only
# or Help → Dependency independence… in the desktop app
```

## Matrix

| Surface | Capability | Today | If system VLC / libvlc removed | If ffmpeg/ffprobe CLI removed | FOSS target |
|---------|------------|-------|--------------------------------|-------------------------------|-------------|
| **Desktop** | A/V decode, volume 0–200, WID embed | libvlc via `libvlc_ffi` | **Hard fail** without staged/bundled `native_core/`; **survives** with complete staged tree (`e2e_native_core_bundle.py`) | Playback OK | Phase 7: bundled libavcodec + demux + HW; retire system VLC |
| **Desktop** | python-vlc | **Absent** (1.99.0) | N/A | N/A | Keep absent |
| **Desktop** | Scan / meta / thumbs / spectrum | `vox_scan` + ffmpeg CLI / `vox_meta` | Unaffected | Meta/thumbs/viz degrade | Linked libav in workers |
| **Android / GrapheneOS** | On-device A/V | Media3 → MediaCodec | Unaffected (never used VLC) | Unaffected | Stay Media3; no GMS |
| **Quest** | 2D panel | Same Media3 companion | Unaffected | Unaffected | Same; honest PiP/panel limits |
| **Codecs H.264 / H.265 / AV1 / Opus** | Decode | Desktop: VLC plugins; Android: MediaCodec | Desktop fails without replacement | Probe only | **Wrap FOSS** (libav, dav1d, MediaCodec) — **do not invent** in-tree x264/x265 |

## This machine (dev profile)

Typical Arch/Manjaro workspace with `pacman -S vlc`:

| Action | Result |
|--------|--------|
| Uninstall `python-vlc` | **OK** — already the supported state |
| `pacman -Rns vlc` (no staged `native_core/`) | Desktop **will not start** |
| Stage then remove system VLC | Desktop can load core from `native_core/` (proven by isolation e2e; libc/dbus stay system) |
| Remove `ffmpeg` only | Playback continues; thumbnails / Help codec probe / spectrum degrade |
| Android/Quest APK | Unrelated — Media3 only |

## Codec policy (opsec-aligned)

- **Do not** ship greenfield H.264 / x264 / H.265 / x265 implementations in-tree.
- **Do** wrap maintained FOSS decoders and platform MediaCodec; document LGPL/GPL plugin license inventory when bundling.
- Encoders (x264/x265) are out of scope until a product encode/export feature exists; the player needs **decoders**.

## Phase 7 (ROADMAP)

See ROADMAP items **76+** for staged work: matrix (done), complete native_core CI, parallel libav backend, retire system VLC, meta off CLI, Android codec fixture matrix.
