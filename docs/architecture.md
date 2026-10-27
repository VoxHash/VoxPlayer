# Architecture

```
QApplication
└── VoxPlayerMainWindow (four-pane shell)
    ├── LeftRail (home / library / browse / favorites / open / torrent)
    ├── Center stack
    │   ├── HomeView (library grid + filters)  ← drop = index only
    │   └── Stage (QVideoWidget embed surface)
    ├── NowPlayingPanel (+ Up next)           ← drop = play immediately
    ├── TransportBar (seek, volume, mute)     ← drop = play immediately
    ├── PlaybackEngine → native C media core only (Vox libvlc_ffi + system/bundled libvlc)
    ├── PlaylistWidget (internal Up next model)
    ├── native_scan / native_workers (optional Rust vox_scan + vox_meta)
    ├── Settings (QSettings wrapper)
    ├── Subtitle manager
    ├── TorrentStreamer (QThread → qbittorrent-api → qBittorrent Web UI)
    └── UpdateChecker (QThread → GitHub Releases API)
```

## Layout on disk

| Path | Role |
|------|------|
| `app.py` | Thin launcher re-exporting `voxplayer.app` |
| `voxplayer/app.py` | Main window, torrent, settings, playlists, zone drops |
| `voxplayer/theme.py` | Bundled palettes + user JSON theme packs; live `COLORS` + stylesheet |
| `voxplayer/library_index.py` | Fingerprints + play stats; incremental re-scan / watch-folder support |
| `voxplayer/ui/shell.py` | Shell widgets (rail, home, now playing, transport) |
| `voxplayer/engine/playback.py` | native-C-core-only playback (volume 0–200, mute) |
| `voxplayer/engine/libvlc_ffi.py` | Vox-owned ctypes binding to libvlc (no python-vlc) |
| `voxplayer/engine/libav_engine.py` | FOSS libav backend (PyAV); `VOXPLAYER_DECODE=libav` or auto-fallback |
| `voxplayer/engine/decode_preflight.py` | libvlc vs libav probe; system VLC optional when libav works |
| `voxplayer/media/libav_io.py` | Linked FOSS tags / posters / PCM (PyAV); ffmpeg CLI optional |
| `voxplayer/codec_fixtures.py` | H.264 / HEVC / AV1 / Opus FOSS encode→decode fixture matrix |
| Android `CodecFixtureMatrix.kt` | Per-device MediaCodec probe (GrapheneOS-honest) |
| `voxplayer/engine/independence.py` | Dependency matrix probe (VLC/ffmpeg/Media3 honesty) |
| `docs/independence_matrix.md` | Opsec/e2e matrix: what breaks if VLC/ffmpeg removed |
| `voxplayer/native_scan.py` | ctypes loader for Rust `vox_scan` |
| `voxplayer/native_workers.py` | ctypes loader + Qt bridge for Rust `vox_meta` worker pool |
| `native/` | Cargo workspace (`vox_scan`, `vox_meta`) + Zig `vox_scan_zig` |
| `run.py` | Launcher: prefer `.venv`, preflight the native C media core |
| `voxplayer/native_core_paths.py` | Discover / activate bundled or system native C media core |
| `voxplayer.spec` + `packaging/` | PyInstaller onedir + clear per-OS native-core installers |
| `test.py` | Smoke tests |
| `docs/` | User and integrator documentation |

## Design notes

- UI language: **Python + PyQt6** (shell only — not a second playback engine)
- Decode / volume path: **native C media core only** via Vox `libvlc_ffi`. Missing system/bundled libvlc → clear install error (no silent Qt Multimedia playback; no third-party Python media binding)
- Prefer **X11 / XWayland** for WID video embed (force `QT_QPA_PLATFORM=xcb` when `DISPLAY` is set); soft rebind on show/resize, hard rebind only when the native window is recreated
- Probe future libvlc Wayland surface bind when present; skip XID bind on pure Wayland without that API (no second media stack)
- Seeks are coalesced and non-blocking (scrub vs exact); on pure Wayland audio volume still works when embed is limited
- Optional **Rust** hot paths: `cargo build --release --manifest-path native/Cargo.toml` → `libvox_scan.so` + `libvox_meta.so`
- Optional **Zig** scanner (Phase 3): `native/vox_scan_zig/build.sh` → lighter `libvox_scan_zig.so`
- **Phase 6**: `vox_scan_dir_meta` + Rust `vox_scan_quick_ids`; loader prefers meta/quick-id capable libs
- Set `VOXPLAYER_NATIVE_DIR` to override where shared libraries are loaded from
- Further native work is tracked in `ROADMAP.md`
- Torrent mode drives an external qBittorrent instance
- Window geometry, volume, and resume data live in platform `QSettings` storage

## Environment knobs

| Variable | Effect |
|----------|--------|
| `VOXPLAYER_FORCE_WAYLAND=1` | Do not force `QT_QPA_PLATFORM=xcb` |
| `VOXPLAYER_KEEP_QPA=1` | Leave existing Qt platform plugin unchanged |
| `DISPLAY` | When set, default to xcb for more reliable video embed |
| `VOXPLAYER_NATIVE_DIR` | Directory containing built `libvox_scan` / `libvox_meta` (or their `target/`) |
| `QB_HOST` / `QB_USERNAME` / `QB_PASSWORD` | qBittorrent Web UI |

`VOXPLAYER_ENGINE=qt` / `VOXPLAYER_FORCE_QT` are **no longer supported** for playback.
