# VoxPlayer

[![PyPI](https://img.shields.io/pypi/v/voxplayer.svg)](https://pypi.org/project/voxplayer/)
[![PyPI downloads](https://img.shields.io/pypi/dm/voxplayer.svg)](https://pypi.org/project/voxplayer/)
[![License](https://img.shields.io/github/license/VoxHash/VoxPlayer)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org/)
[![PyQt6](https://img.shields.io/badge/pyqt6-6.0+-blue.svg)](https://pypi.org/project/PyQt6/)

> A modern desktop media player for Windows, macOS, and Linux. Library rail, responsive home grid, streaming-style now playing, transport bar, **native-C-core-only** decode (0–200% volume), and qBittorrent streaming.

Maintained by **VoxHash Technologies** · contact@voxhash.dev

```bash
pip install voxplayer
voxplayer
```

## Features

- **Modern shell**: Left library rail, responsive grid/list library, now-playing panel, bottom transport — video stage only when needed
- **Universal format support**: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V, MP3, FLAC, WAV, OGG, M4A, AAC, WMA
- **native C media core only**: Native 0–200% volume and mute; clear install error if libvlc/python-vlc is missing (no Qt playback fallback)
- **Zone drag-and-drop**: Library grid indexes; Now Playing / Up next / transport play immediately
- **Native scan (optional)**: Rust/Zig `vox_scan` with parallel meta + quick ids (`cargo build --release --manifest-path native/Cargo.toml`)
- **Thumbnails & live preview**: Smart ffmpeg posters (skips black frames); live frame grabs in Now Playing / transport
- **Metadata enrichment**: Offline-first local tags; Audio browse by year / genre / artist; Video browse by movies / TV seasons
- **Up next & playlists**: Click Up next to play; icon clear-and-stop; Favorites chips plus named local playlists by file path
- **Torrent streaming**: qBittorrent API client included in main install deps, with media-library gating
- **Tray background**: Minimize / close-to-tray while playback continues
- **Daemon remotes**: `voxplayer-tui` / `voxplayer-ctl` and browser UI at `http://127.0.0.1:17890/ui/`
- **Android / Quest app**: desktop-matched ember shell; Quest panel 1024×640; background Media3 session, gapless queues, repeat/shuffle, queue reorder, volume 0–200%, sound output + AOSP EQ, headset ±15s seek, Quest route fallback, sleep timer, local bookmarks, on-device Recent/Top/Week/Month listening stats, playlist folders + smart lists, local lyrics sidecars, soft fade-in transitions, home-screen media widget, rich AVRCP metadata, landscape driving layout, Quest/foldable multi-window polish, offline artwork thumbnails, local library search, DLNA cast (no GMS), offline share card, playback resumption, richer Now Playing; Connect via Wi‑Fi or Bluetooth RFCOMM; playlist/podcast sync; no GMS
- **LAN VPN bypass**: `voxplayer-lan-bypass` keeps home/RFC1918 traffic off the VPN path for phone/Quest remotes
- **Desktop bundles**: onedir builds can ship the native C media core; clear per-OS installers under `packaging/`
- **File associations**: Double-click media to open with VoxPlayer
- **Cross-platform**: Windows, macOS, and Linux

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Quick Start

```bash
pip install voxplayer
voxplayer "path/to/video.mp4"
```

System **libvlc** is required (e.g. `pacman -S vlc` / `apt install vlc libvlc-dev` / `brew install vlc`). Prefer launching with `python run.py` so the project `.venv` and engine preflight run.

Optional metadata extras:

```bash
pip install "voxplayer[metadata]"
```

## Installation

### Method 1: PyPI (recommended)

```bash
pip install voxplayer
voxplayer
```

Package page: [https://pypi.org/project/voxplayer/](https://pypi.org/project/voxplayer/)

### Method 2: Download Executable

**Windows:**
1. Download `VoxPlayer.exe` from [Releases](https://github.com/VoxHash/VoxPlayer/releases)
2. Run `VoxPlayer.exe` to start
3. Run `register_file_associations.bat` as Administrator for file associations

**macOS / Linux:** download the matching asset from [Releases](https://github.com/VoxHash/VoxPlayer/releases) when published for your platform.

### Method 3: Python (source)

```bash
git clone https://github.com/VoxHash/VoxPlayer.git
cd VoxPlayer
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py "path/to/video.mp4"
```

Optional faster library folder scans:

```bash
cargo build --release --manifest-path native/Cargo.toml
```

### Method 4: Built wheel (from source)

```bash
pip install build
python -m build
pip install dist/voxplayer-*.whl
voxplayer
```

### System dependencies

| Dependency | Required? | Notes |
|------------|-----------|-------|
| Python 3.8+ (3.10–3.12 recommended) | Yes | Runtime |
| PyQt6 | Yes | Installed via `requirements.txt` |
| FFmpeg (Qt backend / system) | Recommended | Playback codecs; `ffmpeg` CLI useful for debugging |
| qBittorrent Web UI | Optional | Torrent streaming only |
| Alternate media client | Optional | Useful to compare problem files |

## Usage

### Opening media

- **Double-click** after file associations are registered
- **Command line:** `python app.py "path/to/video.mp4"`
- **Drag & drop** files or folders onto the window

### Playlist

- Add via File menu or drag & drop
- Search/filter in the playlist dock
- Import/export M3U, PLS, XSPF

### Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Play/Pause |
| `Left`/`Right` | Seek |
| `Up`/`Down` | Volume |
| `M` | Mute/Unmute |
| `F11` | Fullscreen |
| `Ctrl+O` | Open file(s) |
| `Ctrl+L` | Toggle playlist |
| `Ctrl+Q` | Quit |

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| Audio Output | Default or manual device | Default |
| Volume | Master volume | 50% |
| Theme | View → Theme (Ember / Midnight / Slate / Graphite + user JSON packs) | Ember |
| Auto-Update | GitHub update checks | Enabled |
| Update Channel | Stable or Beta | Stable |

### Environment variables (torrent streaming)

| Variable | Default | Purpose |
|----------|---------|---------|
| `QB_HOST` | `localhost:8080` | qBittorrent Web UI host:port |
| `QB_USERNAME` | empty | Web UI username |
| `QB_PASSWORD` | empty | Web UI password (never commit) |
| `QT_QPA_PLATFORM` | unset | Use `offscreen` for headless tests |

See [docs/configuration.md](docs/configuration.md) for details.

## Documentation

- [docs/index.md](docs/index.md) — documentation home
- [docs/quick-start.md](docs/quick-start.md)
- [docs/installation.md](docs/installation.md)
- [docs/usage.md](docs/usage.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
- [CHANGELOG.md](CHANGELOG.md)
- [ROADMAP.md](ROADMAP.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [SUPPORT.md](SUPPORT.md)

## Roadmap

Planned milestones live in [ROADMAP.md](ROADMAP.md).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) and use the PR template. Run:

```bash
QT_QPA_PLATFORM=offscreen python test.py
```

## Security

Report vulnerabilities via [SECURITY.md](SECURITY.md) or email contact@voxhash.dev.

## License

MIT — see [LICENSE](LICENSE).

---

Made by VoxHash Technologies
