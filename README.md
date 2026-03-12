# VoxPlayer

[![Version](https://img.shields.io/badge/version-1.0.1-blue.svg)](https://github.com/voxhash/voxplayer)
[![License](https://img.shields.io/github/license/voxhash/voxplayer)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org/)
[![PyQt6](https://img.shields.io/badge/pyqt6-6.0+-blue.svg)](https://pypi.org/project/PyQt6/)]

> A modern, ultra-compact media player for Windows, macOS, and Linux with professional file association support. Built with PyQt6 and designed for simplicity and performance.

## ✨ Features

- **Universal Format Support**: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V, MP3, FLAC, WAV, OGG, M4A, AAC, WMA
- **Ultra-Compact Design**: Minimalist interface with maximum functionality
- **True Volume Amplification**: Up to 200% volume boost for quiet media
- **Professional File Associations**: Double-click any media file to open with VoxPlayer
- **Advanced Playlist Management**: Smart playlist behavior with search, filtering, and import/export
- **Torrent Streaming**: qBittorrent integration for streaming media
- **Auto-Update System**: GitHub-based update checking
- **Cross-Platform**: Windows, macOS, and Linux support

## 🧭 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [Examples](#-examples)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Quick Start

```bash
# 1) Install dependencies
pip install -r requirements.txt

# 2) Run VoxPlayer
python app.py

# Or with a file
python app.py "path/to/video.mp4"
```

## 💿 Installation

### Method 1: Download Executable (Recommended)

**Windows:**
1. Download `VoxPlayer.exe` from [Releases](https://github.com/voxhash/voxplayer/releases)
2. Run `VoxPlayer.exe` to start
3. Run `register_file_associations.bat` as Administrator for file associations

**macOS:**
1. Download `VoxPlayer-1.0.0-macOS.dmg` from [Releases](https://github.com/voxhash/voxplayer/releases)
2. Install by dragging VoxPlayer.app to Applications
3. Launch from Applications folder

**Linux:**
- **Debian/Ubuntu**: `sudo dpkg -i voxplayer_1.0.0_amd64.deb`
- **Fedora/CentOS/RHEL**: `sudo dnf install voxplayer-1.0.0-1.x86_64.rpm`
- **Arch Linux**: `sudo pacman -U voxplayer-1.0.0-1-x86_64.pkg.tar.zst`

### Method 2: Python Installation

```bash
git clone https://github.com/voxhash/voxplayer.git
cd voxplayer
pip install -r requirements.txt
python app.py
```

### Method 3: Source Distribution

```bash
pip install VoxPlayer-1.0.0.tar.gz
voxplayer
```

## 🛠 Usage

### Opening Media Files

- **Double-Click**: Set up file associations, then double-click any media file
- **Command Line**: `python app.py "path/to/video.mp4"`
- **Drag & Drop**: Drag files/folders onto VoxPlayer window

### Playlist Management

- **Add Files**: File → Open File(s) or Open Folder, or drag & drop
- **Search**: Type in search box to filter playlist
- **Remove Items**: Click X button next to any item
- **Import/Export**: File → Import/Export Playlist (M3U, PLS, XSPF)

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Play/Pause |
| `Left/Right` | Seek backward/forward |
| `Up/Down` | Volume up/down |
| `M` | Mute/Unmute |
| `F11` | Toggle fullscreen |
| `Ctrl+O` | Open file(s) |
| `Ctrl+L` | Toggle playlist |
| `Ctrl+Q` | Quit |

## ⚙️ Configuration

### Settings Menu

Access via **File → Settings** or `Ctrl+,`:

| Setting | Description | Default |
|---------|-------------|---------|
| Audio Output | Default or Manual device selection | Default |
| Volume | Master volume level | 50% |
| Theme | Dark theme (default) | Dark |
| Auto-Update | Enable/disable update checking | Enabled |
| Update Channel | Stable or Beta updates | Stable |

### File Associations

- **Register**: `register_file_associations.bat` (run as Administrator)
- **Unregister**: `unregister_file_associations.bat`
- **Test**: `test_file_associations.bat`

## 📚 Examples

### Basic Usage

```bash
# Play a video file
python app.py "movie.mp4"

# Play an audio file
python app.py "song.mp3"
```

### Advanced Usage

- Drag multiple files/folders to create a playlist
- Use search to filter large playlists
- Export playlists for backup or sharing
- Use keyboard shortcuts for efficient control

## 🗺 Roadmap

Planned milestones live in [ROADMAP.md](ROADMAP.md). For changes, see [CHANGELOG.md](CHANGELOG.md).

**Upcoming Features:**
- Enhanced format support (HEVC, AV1, Opus)
- Audio equalizer with presets
- Playlist shuffle and repeat modes
- Plugin system architecture
- Cloud storage integration

## 🤝 Contributing

We welcome PRs! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and follow the PR template.

## 🔒 Security

Please report vulnerabilities via [SECURITY.md](SECURITY.md).

## 📄 License

This project is licensed under the terms in [LICENSE](LICENSE).

## 📚 Documentation

- **[Changelog](CHANGELOG.md)** - Version history
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute
- **[Roadmap](ROADMAP.md)** - Development roadmap
- **[Development Goals](DEVELOPMENT_GOALS.md)** - Technical goals
- **[Support](SUPPORT.md)** - Getting help

## 🎉 Acknowledgments

- **PyQt6** - Cross-platform GUI framework
- **FFmpeg** - Media processing backend
- **qBittorrent** - Torrent streaming integration
- **Community** - Feedback and contributions

---

**Made with ❤️ by VoxHash**

*VoxPlayer - Professional media playback made simple!* 🎬✨
