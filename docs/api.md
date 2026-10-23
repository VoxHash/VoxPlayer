# API

VoxPlayer is primarily a desktop application. The installable package exposes a small Python surface for launching the UI.

## Package

```python
import voxplayer

print(voxplayer.__version__)
```

Entry point (console script `voxplayer`):

```python
from voxplayer.app import main

main()
```

## Notable classes

| Symbol | Module | Role |
|--------|--------|------|
| `VoxPlayerMainWindow` | `voxplayer.app` / `app` | Main window and player UI |
| `TorrentStreamer` | `voxplayer.app` / `app` | Background qBittorrent streaming thread |
| `UpdateChecker` | `voxplayer.app` / `app` | GitHub release update checks |
| `Settings` | `voxplayer.app` / `app` | Thin wrapper around `QSettings` |

## Control daemon (localhost / trusted LAN)

While the desktop app is running (unless `VOXPLAYER_DAEMON=0`), a small HTTP JSON API listens on `127.0.0.1:17890` by default. Non-loopback binds require `VOXPLAYER_DAEMON_ALLOW_LAN=1`.

| Method | Path | Notes |
|--------|------|--------|
| GET | `/status` | Now playing, position, volume, version |
| GET | `/library?limit=&offset=` | Read-only indexed library for companions |
| POST | `/play` `/pause` `/playpause` `/stop` `/next` `/previous` | Transport |
| POST | `/volume` | Body `{"percent": 0-200}` |
| POST | `/seek` | Body `{"ms": int}` or `{"relative_ms": int}` |
| POST | `/open` | Body `{"path": "/abs/file"}` |
| GET | `/ui/` | Packaged browser remote |

The Android companion under `android/` uses this API over LAN or `adb reverse`.
