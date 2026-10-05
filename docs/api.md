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

There is no HTTP server or public REST API. Integrate by launching the process or embedding `VoxPlayerMainWindow` inside another Qt application (advanced; not officially supported).
