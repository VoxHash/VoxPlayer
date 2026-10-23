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
    ├── native_scan (optional Rust vox_scan cdylib)
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
| `voxplayer/theme.py` | VoxPlayer visual identity / stylesheet |
| `voxplayer/ui/shell.py` | Shell widgets (rail, home, now playing, transport) |
| `voxplayer/engine/playback.py` | native-C-core-only playback (volume 0–200, mute) |
| `voxplayer/native_scan.py` | ctypes loader for Rust `vox_scan` |
| `native/` | Cargo workspace (`vox_scan` parallel folder scanner) |
| `run.py` | Launcher: prefer `.venv`, preflight the native C media core |
| `test.py` | Smoke tests |
| `docs/` | User and integrator documentation |

## Design notes

- UI language: **Python + PyQt6** (shell only — not a second playback engine)
- Decode / volume path: **native C media core only**. Missing python-vlc or system libvlc → clear install error (no silent Qt Multimedia playback)
- Prefer **X11 / XWayland** for WID video embed; on pure Wayland audio volume still works via native C media core
- Optional **Rust** hot path: `cargo build --release --manifest-path native/Cargo.toml` → `libvox_scan.so` for parallel library walks
- Further native phases (metadata workers, Zig experiments) are tracked in `ROADMAP.md`
- Torrent mode drives an external qBittorrent instance
- Window geometry, volume, and resume data live in platform `QSettings` storage

## Environment knobs

| Variable | Effect |
|----------|--------|
| `VOXPLAYER_FORCE_WAYLAND=1` | Do not force `QT_QPA_PLATFORM=xcb` |
| `VOXPLAYER_KEEP_QPA=1` | Leave existing Qt platform plugin unchanged |
| `DISPLAY` | When set, default to xcb for more reliable video embed |
| `QB_HOST` / `QB_USERNAME` / `QB_PASSWORD` | qBittorrent Web UI |

`VOXPLAYER_ENGINE=qt` / `VOXPLAYER_FORCE_QT` are **no longer supported** for playback.
