# Architecture

```
QApplication
└── VoxPlayerMainWindow
    ├── QMediaPlayer + QAudioOutput + QVideoWidget
    ├── Playlist dock / search
    ├── Settings (QSettings wrapper)
    ├── Subtitle manager
    ├── TorrentStreamer (QThread → qbittorrent-api → qBittorrent Web UI)
    └── UpdateChecker (QThread → GitHub Releases API)
```

## Layout on disk

| Path | Role |
|------|------|
| `app.py` | Primary application module used by `run.py` and local launches |
| `voxplayer/app.py` | Packaged copy exposed as `voxplayer.app` |
| `run.py` | Thin launcher with Qt logging defaults |
| `test.py` | Smoke tests (imports, window create, torrent classes) |
| `docs/` | User and integrator documentation |

## Design notes

- Playback uses Qt Multimedia (FFmpeg backend on modern Qt builds)
- Torrent mode does not embed a BitTorrent stack; it drives an external qBittorrent instance
- Window geometry, volume, and resume data live in platform `QSettings` storage
