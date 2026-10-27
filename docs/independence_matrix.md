# Dependency independence matrix

Honest status through **1.103.0** (system libvlc optional when FOSS libav works).

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
| **Desktop** | A/V decode, volume 0–200, WID embed | libvlc via `libvlc_ffi` (default); optional `VOXPLAYER_DECODE=libav` (PyAV) | **Hard fail** without staged/bundled `native_core/` on libvlc path; **survives** with complete staged tree; libav path needs FFmpeg libs + `voxplayer[libav]` (no libvlc) | Playback OK | Phase 7: make libav default-capable; retire required system VLC |
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
| `pacman -Rns vlc` with `voxplayer[libav]` | Desktop **auto-falls back** to FOSS libav (`e2e_no_system_vlc.py`) |
| `pacman -Rns vlc` without libav and without staged `native_core/` | Desktop **will not start** |
| Stage then remove system VLC | Desktop can load libvlc from `native_core/` (isolation e2e) |
| Remove `ffmpeg` only | libvlc path OK; libav path / thumbs / spectrum degrade |
| Android/Quest APK | Unrelated — Media3 only |

## Codec policy (opsec-aligned)

- **Do not** ship greenfield H.264 / x264 / H.265 / x265 implementations in-tree.
- **Do** wrap maintained FOSS decoders and platform MediaCodec; document LGPL/GPL plugin license inventory when bundling.
- Encoders (x264/x265) are out of scope until a product encode/export feature exists; the player needs **decoders**.

## Phase 7 (ROADMAP)

See ROADMAP items **76+** for staged work: matrix (done), complete native_core CI, parallel libav backend, retire system VLC, meta off CLI, Android codec fixture matrix.
