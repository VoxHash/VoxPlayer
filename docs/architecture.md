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
    ├── PlaybackEngine → native C media core only (python-vlc + system libvlc)
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
| `voxplayer/ui/shell.py` | Shell widgets (rail, home, now playing, transport) |
| `voxplayer/engine/playback.py` | native-C-core-only playback (volume 0–200, mute) |
| `voxplayer/native_scan.py` | ctypes loader for Rust `vox_scan` |
| `voxplayer/native_workers.py` | ctypes loader + Qt bridge for Rust `vox_meta` worker pool |
| `native/` | Cargo workspace (`vox_scan`, `vox_meta`) + Zig `vox_scan_zig` |
| `run.py` | Launcher: prefer `.venv`, preflight the native C media core |
| `test.py` | Smoke tests |
| `docs/` | User and integrator documentation |

## Design notes

- UI language: **Python + PyQt6** (shell only — not a second playback engine)
- Decode / volume path: **native C media core only**. Missing python-vlc or system libvlc → clear install error (no silent Qt Multimedia playback)
- Prefer **X11 / XWayland** for WID video embed; soft rebind on show/resize, hard rebind only when the native window is recreated
- Seeks are coalesced and non-blocking (scrub vs exact); on pure Wayland audio volume still works when embed is limited
- Optional **Rust** hot paths: `cargo build --release --manifest-path native/Cargo.toml` → `libvox_scan.so` + `libvox_meta.so`
- Optional **Zig** scanner (Phase 3): `native/vox_scan_zig/build.sh` → lighter `libvox_scan_zig.so` (preferred over Rust when both exist)
- Set `VOXPLAYER_NATIVE_DIR` to override where shared libraries are loaded from
- Further native phases (Zig experiments, WID harden) are tracked in `ROADMAP.md`
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
