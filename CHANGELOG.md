# Changelog — VoxPlayer

All notable changes to VoxPlayer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Playlist shuffle and repeat modes
- Persist library roots across sessions
- Broader subtitle format support where maintainable
- Skin/theme packs; optional local control daemon; Android / GrapheneOS companion phase

## [1.3.1] - 2026-10-23

### Fixed
- libmpv startup segfault under non-C locales (`LC_NUMERIC=C` before engine init)
- Native-engine install dialog no longer cites third-party GitHub installation URLs

## [1.3.0] - 2026-10-23

### Added
- **Zone-aware drag-and-drop**: drop on Home/library grid → **index only**; drop on Now Playing / Up next / bottom transport → **add and play immediately**
- **Rust `vox_scan` native scanner** (`native/vox_scan`) with Python ctypes loader for parallel folder walks; Python walker remains if the `.so` is not built
- Clear **libmpv install guidance** on Linux / Windows / macOS when python-mpv or system libmpv is missing (`run.py` preflight + startup dialog)

### Changed
- **libmpv is the only playback engine** — Qt Multimedia is no longer a playback fallback (PyQt6 remains the UI shell; `QVideoWidget` is an embed surface only)
- Volume **0–200%** and mute use engine-native libmpv properties only (no Pulse/`pactl` design path)
- Filter tabs **All / Video / Audio / Recent** use understated icon+text controls instead of heavy filled chips
- Home library and Up next **scrollbars** are wider, higher-contrast, and easier to grab on the dark theme
- Default logical volume for new installs is **100%**; engine label always reports libmpv (embedded or audio path)
- ROADMAP expanded: native Rust/Zig/C phases, skin/daemon/podcast-like feeds, portable-player concepts, Android/GrapheneOS — without third-party brand names

### Fixed
- Volume slider and speaker mute fighting each other when the engine was on the old Qt path
- `run.py` ensuring the project `.venv` (with `python-mpv`) is the interpreter users actually launch

### Removed
- Silent fallback from libmpv failures to Qt Multimedia playback
- Recursive “accept drops everywhere” behavior that broke zone-specific drop routing

## [1.2.1] - 2026-10-23

### Changed
- Now Playing header keeps Expand / Minimize only in the ⋯ menu (standalone icon buttons removed)
- Up next **Clear** is an icon-only control with tooltip “Clear Up next and stop”
- Right-side **Queue** dock removed; Up next under Now Playing is the only queue UI
- Library facets: **Audio** shows Year / Genre / Artist; **Video** shows Movies / TV Shows; **Type** facet removed; All / Recent hide the facet row
- Save to playlist offers existing playlists plus “Create new…”
- `run.py` prefers the project `.venv` interpreter so torrent deps resolve consistently

### Fixed
- Favorites context menu shows **Remove from Favorites** when the item is already saved
- Named playlists appear as selectable chips in Favorites & playlists and open to their tracks
- Clearing Up next fully stops playback and resets Now Playing / transport title, art, and time

## [1.2.0] - 2026-10-23

### Added
- **Streaming-style Now Playing**: header with More menu, large rounded cover, click art to expand
- **Grid / List toggle** with responsive grid columns that reflow on resize
- **Library browse facets**: year, genre, artist, movies (chronological), TV by season
- **Favorites & local playlists** persisted under `~/.local/share/voxplayer/playlists/` (file paths)
- **System tray**: minimize / close-to-tray keeps audio and video playing; restore from tray
- **Modern About modal** with VoxPlayer branding, version, and copyright
- Up next: click to play, right-click remove, Clear Up next and stop, Add to queue from library

### Changed
- **libmpv is the default engine** when available — reliable 0–200% volume without requiring `VOXPLAYER_ENGINE` or Pulse-only workarounds for the happy path
- **Audio no longer opens the empty center stage**; video stage shows for video playback or when the user expands Now Playing
- `qbittorrent-api` and `python-mpv` moved into **main install dependencies**
- Up next lives in the Now Playing rail

### Fixed
- Video poster/thumbnail capture skips near-black frames and retries multiple seek points
- Torrent import no longer fails with “qbittorrent-api not available” on a normal `pip install voxplayer`

## [1.1.1] - 2026-10-22

### Fixed
- **Volume accuracy**: Media Information reports the same 0–200% logical volume as the transport slider (no longer Qt’s clamped 0–100%)
- **Volume boost**: Qt path applies PipeWire/PulseAudio per-stream gain above 100%; libmpv uses native volume 0–200
- **Now Playing / transport art**: live video frame grabs while playing; ffmpeg/cache thumbnails for library cards and transport
- **Torrent gating**: reject non-media torrents (ISO/distro/archives) before add; re-check after client metadata

### Added
- Metadata enrichment via ffprobe/mutagen tags, MusicBrainz, optional AcoustID (`ACOUSTID_API_KEY`), optional TMDB (`TMDB_API_KEY`), Cover Art Archive
- Offline-first metadata: disk cache (`~/.cache/voxplayer/metadata/`), fetch-once per file identity, **View → Refresh Metadata** / library refresh
- Optional extras: `pip install "voxplayer[metadata]"`

## [1.1.0] - 2026-10-22

### Added
- **Modern shell**: left library rail, center home/stage, now-playing panel, bottom transport bar
- **VoxPlayer identity**: ember-on-charcoal theme (unique product look)
- **Home library grid** with All / Video / Audio / Recent filters and search
- **Playback engine abstraction** with Qt Multimedia default and optional libmpv (`pip install "voxplayer[native]"`)
- Hardware-decode hints for Qt FFmpeg (`QT_FFMPEG_DECODING_HW_DEVICE_TYPES`) and libmpv `hwdec=auto-safe` when embedded

### Changed
- Root `app.py` is a thin launcher; packaged implementation remains `voxplayer/app.py`
- Default window size and layout oriented for the four-pane desktop shell
- ROADMAP updated for phased native-core migration

### Fixed
- Clearer engine status in the now-playing panel

## [1.0.4] - 2026-10-05

### Added
- **PyPI**: Published `voxplayer` 1.0.4 to [PyPI](https://pypi.org/project/voxplayer/) (`pip install voxplayer`)
- README PyPI badges and install path at the top of the project page

### Fixed
- **qBittorrent localhost**: Prefer unauthenticated loopback connects so a wrong `QB_PASSWORD` no longer triggers WebUI IP bans on `127.0.0.1`
- **Torrent add**: Treat newer `TorrentsAddedMetadata` WebAPI success responses as a successful add

## [1.0.3] - 2026-10-05

### Fixed
- **CI Lint**: Style flake8 report is advisory (critical undefined-name/syntax checks still hard-fail), matching black/mypy policy
- **Linux Build**: Replace obsolete `libgl1-mesa-glx` with Noble-compatible `libgl1`/`libegl1` packages in `build.yml`
- Trailing whitespace cleaned in `app.py` / `voxplayer/app.py` for cleaner diffs

## [1.0.2] - 2026-10-05

### Added
- Complete documentation kit under `docs/` (getting started, install, configuration, usage, CLI, API, architecture, troubleshooting, FAQ, examples)
- GitHub issue templates (bug, feature, docs) and pull request template

### Changed
- README and ROADMAP aligned with current product state (October 2026)
- Contact metadata standardized to `contact@voxhash.dev` / VoxHash Technologies
- `.gitignore` expanded for workstation scratch copies and common local junk

### Removed
- `DEVELOPMENT_GOALS.md` (superseded by `ROADMAP.md` and the docs kit)

### Fixed
- Support/docs links that pointed at a missing `docs/` tree

## [1.0.1] - 2026-03-12

### Added
- **CI/CD Pipeline**: Complete GitHub Actions workflows
  - Continuous Integration workflow with linting and testing across Python 3.8-3.12
  - Cross-platform build workflow (Windows, macOS, Linux)
  - Automated release workflow for version tags
  - CodeQL security analysis workflow
- **Documentation Files**:
  - `CODE_OF_CONDUCT.md` - Community code of conduct
  - `SECURITY.md` - Security policy and vulnerability reporting
  - `SUPPORT.md` - Support information and getting help
- **Repository Configuration**:
  - Comprehensive `.gitignore` with Python, Node.js, and build artifacts
  - `.gitattributes` for consistent line endings

### Changed
- **Documentation Restructure**: Updated all documentation files for consistency
  - `README.md` - Restructured with table of contents and improved organization
  - `CONTRIBUTING.md` - Streamlined with conventional commits and testing guidelines
  - `ROADMAP.md` - Simplified with quarterly milestones
  - `DEVELOPMENT_GOALS.md` - Organized with short-term and mid-term goals
- **Code Quality**:
  - Cleaned up duplicate and unused imports in `app.py`
  - Improved code formatting and consistency
- **Build Scripts**:
  - Updated `build_source.sh` to remove GITHUB_TOPICS.md references

### Removed
- `GITHUB_TOPICS.md` - Removed file and all references from documentation
- Duplicate imports (tempfile, os, shutil)
- Unused imports (threading, hashlib, urllib.parse, subprocess, asdict, and various PyQt6 components)

### Fixed
- Fixed duplicate imports in `app.py`
- **Volume Amplification**: Implemented true digital pre-amp for 0-200% volume boost
  - Direct sample multiplication (0.0-2.0x gain)
  - Proper clipping handling and user warnings
  - Consistent volume application across all audio output paths
- **Torrent Streaming**: Enhanced sequential download and buffering
  - Sequential piece downloading (0, 1, 2... n) for smooth playback
  - Intelligent buffering thresholds (10MB MP4, 20MB MKV)
  - File priority selection for optimal streaming
  - Real-time playback while downloading
  - qBittorrent API compatibility fixes
- **CI/CD**: Resolved Windows Unicode encoding errors
- **Code Quality**: Removed duplicate imports and improved error handling
- Removed unused PyQt6 imports (QSize, QMimeData, QFont, QColor, QPixmap, QProgressBar, QComboBox, QCheckBox, QSpinBox, QColorDialog, QAudioDevice)
- Fixed code formatting issues
- Removed duplicate blank lines

## [1.0.0] - 2024-12-19

### Added
- **Complete Media Player**: Ultra-compact design with professional UI
- **File Association Support**: Double-click any media file to open with VoxPlayer
- **Command-Line Support**: Direct file opening from command line
- **Advanced Playlist Management**: Smart playlist behavior with search and filtering
- **Torrent Streaming**: qBittorrent integration for streaming media
- **Auto-Update System**: GitHub-based update checking
- **Audio Device Selection**: Default or manual audio output
- **Professional Features**: Fullscreen mode, timeline preview, subtitle support
- **Cross-Platform Support**: Windows, macOS, and Linux distributions
- **Native Packaging**: Professional installers for all platforms
- **Source Distribution**: pip-installable Python package
- **Comprehensive Documentation**: Complete user and developer guides

### Core Features
- **Universal Format Support**: 15+ video and audio formats (MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V, MP3, FLAC, WAV, OGG, M4A, AAC, WMA)
- **Ultra-Compact Design**: Minimalist interface with maximum functionality
- **True Volume Amplification**: Up to 200% volume boost
- **Smart Playlist Behavior**: No auto-clearing, persistent playlist
- **Drag & Drop Support**: Files and folders from Windows Explorer
- **Real-Time Search**: Instant filtering within playlists
- **Import/Export**: M3U, PLS, XSPF, and text format support
- **Individual Item Control**: Remove specific items with X buttons
- **Visual Selection**: Clear indication of current playing item

### Advanced Features
- **Torrent Streaming**: qBittorrent integration for streaming
- **Auto-Update System**: GitHub-based update checking
- **Audio Device Selection**: Default or manual audio output
- **Fullscreen Mode**: Auto-hiding controls for immersive viewing
- **Timeline Preview**: Hover and drag preview on timeline
- **SRT Subtitle Support**: Built-in subtitle display
- **Snapshot Functionality**: Capture frames from videos
- **Context Menus**: Right-click options for advanced features

### User Experience
- **Dark Theme**: Professional dark interface
- **Keyboard Shortcuts**: 15+ shortcuts for efficient control
- **File Associations**: Professional Windows integration
- **Command-Line Interface**: Direct file opening support
- **Settings Menu**: Comprehensive configuration options
- **Help System**: Built-in help and keyboard shortcuts

### Technical Implementation
- **PyQt6 Framework**: Modern cross-platform GUI
- **FFmpeg Backend**: Professional media processing
- **Cross-Platform Build**: Automated build scripts for all platforms
- **Native Packaging**: Platform-specific installers and packages
- **File Associations**: Platform-specific integration
- **GitHub Integration**: Auto-update and release management
