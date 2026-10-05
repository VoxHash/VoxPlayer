# VoxPlayer

[![Version](https://img.shields.io/badge/version-1.0.2-blue.svg)](https://github.com/VoxHash/VoxPlayer)
[![License](https://img.shields.io/github/license/VoxHash/VoxPlayer)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org/)
[![PyQt6](https://img.shields.io/badge/pyqt6-6.0+-blue.svg)](https://pypi.org/project/PyQt6/)

> A modern, ultra-compact media player for Windows, macOS, and Linux with professional file association support. Built with PyQt6 and designed for simplicity and performance.

Maintained by **VoxHash Technologies** · contact@voxhash.dev

## Features

- **Universal Format Support**: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V, MP3, FLAC, WAV, OGG, M4A, AAC, WMA
- **Ultra-Compact Design**: Minimalist interface with maximum functionality
- **True Volume Amplification**: Up to 200% volume boost for quiet media
- **Professional File Associations**: Double-click any media file to open with VoxPlayer
- **Advanced Playlist Management**: Smart playlist behavior with search, filtering, and import/export
- **Torrent Streaming**: qBittorrent Web UI integration for streaming media
- **Auto-Update System**: GitHub-based update checking
- **Cross-Platform**: Windows, macOS, and Linux support

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
git clone https://github.com/VoxHash/VoxPlayer.git
cd VoxPlayer
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python test.py
python app.py "path/to/video.mp4"
```

## Installation

### Method 1: Download Executable (Recommended)

**Windows:**
1. Download `VoxPlayer.exe` from [Releases](https://github.com/VoxHash/VoxPlayer/releases)
2. Run `VoxPlayer.exe` to start
3. Run `register_file_associations.bat` as Administrator for file associations

**macOS / Linux:** download the matching asset from [Releases](https://github.com/VoxHash/VoxPlayer/releases) when published for your platform.

### Method 2: Python (source)

```bash
git clone https://github.com/VoxHash/VoxPlayer.git
cd VoxPlayer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Torrent extras:

```bash
pip install -e ".[torrent]"
```

### Method 3: Built wheel

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
| VLC | Optional | Useful to compare problem files |

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
| Theme | UI theme | Dark |
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
