# Architecture

```
QApplication
└── VoxPlayerMainWindow (four-pane shell)
    ├── LeftRail (home / library / queue / open / torrent)
    ├── Center stack
    │   ├── HomeView (library grid + filters)
    │   └── Stage (QVideoWidget)
    ├── NowPlayingPanel (metadata + up-next)
    ├── TransportBar (seek, volume, prev/next)
    ├── PlaybackEngine
    │   ├── Qt Multimedia (QMediaPlayer + QAudioOutput) — default
    │   └── Optional libmpv embed (C) when VOXPLAYER_ENGINE=mpv / X11
    ├── PlaylistWidget (queue dock)
    ├── Settings (QSettings wrapper)
    ├── Subtitle manager
    ├── TorrentStreamer (QThread → qbittorrent-api → qBittorrent Web UI)
    └── UpdateChecker (QThread → GitHub Releases API)
```

## Layout on disk

| Path | Role |
|------|------|
| `app.py` | Thin launcher re-exporting `voxplayer.app` |
| `voxplayer/app.py` | Main window, torrent, settings, playlists |
| `voxplayer/theme.py` | VoxPlayer visual identity / stylesheet |
| `voxplayer/ui/shell.py` | Shell widgets (rail, home, now playing, transport) |
| `voxplayer/engine/playback.py` | Playback backend abstraction |
| `run.py` | Thin launcher with Qt logging defaults |
| `test.py` | Smoke tests (imports, window create, torrent classes) |
| `docs/` | User and integrator documentation |

## Design notes

- UI language: **Python + PyQt6** (same Qt family used by major desktop media shells)
- Decode path: **Qt Multimedia / FFmpeg** always; optional **libmpv (C)** for hardware-oriented decode when widget embedding works
- Phased native migration is tracked in `ROADMAP.md` — no big-bang C++ rewrite required for day-to-day use
- Torrent mode does not embed a BitTorrent stack; it drives an external qBittorrent instance
- Window geometry, volume, and resume data live in platform `QSettings` storage

## Environment knobs

| Variable | Effect |
|----------|--------|
| `VOXPLAYER_FORCE_QT=1` | Always use Qt Multimedia |
| `VOXPLAYER_ENGINE=mpv` | Prefer libmpv embed (including Wayland opt-in) |
| `VOXPLAYER_ENGINE=qt` | Prefer Qt Multimedia |
| `QB_HOST` / `QB_USERNAME` / `QB_PASSWORD` | qBittorrent Web UI |
