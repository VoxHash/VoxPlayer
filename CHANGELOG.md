# Changelog — VoxPlayer

All notable changes to VoxPlayer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Android / GrapheneOS companion phase
- Library UX: Albums / Artists / Tracks / Liked navigation
- Waveform / spectrum meter as optional transport chrome

## [1.16.0] - 2026-10-23

### Added
- Gapless queue (best-effort): prefetch next audio on a second MediaPlayer from the same libvlc Instance; promote on natural end (Audio → Playback companion)
- Bookmark resume: persist per-file positions and seek on reopen; clear near end / Clear all bookmarks
- On-device library browse for USB `VoxPlayer/` folders (media + M3U) via Media → Portable Devices → Browse On-Device Library…

### Changed
- Natural track end emits `ended` (auto-advance / gapless); user Stop no longer auto-advances the queue
- ROADMAP portable-player companion item marked done

## [1.15.0] - 2026-10-23

### Added
- LAN multi-room transport sync: Audio → Multi-room fans out play/pause/stop/open/seek/volume to peer VoxPlayer control daemons (same native stack; peers need `VOXPLAYER_DAEMON_ALLOW_LAN=1`)
- Manage rooms (add/remove/test/toggle), Sync now, and setup help; config in `~/.config/voxplayer/multiroom.json`
- Inbound daemon commands do not re-broadcast (no leader↔follower echo loops)

### Changed
- ROADMAP multi-room item marked done (no second media / cast SDK)

## [1.14.0] - 2026-10-23

### Added
- Portable / USB device detection (`/proc/mounts` + removable sysfs; `/run/media/$USER` / `/media/$USER`) via Media → Portable Devices → List Detected Devices
- One-action sync of Favorites, named playlists, Up next, or downloaded podcast episodes onto a mounted volume under `VoxPlayer/` with an M3U playlist

### Changed
- ROADMAP portable / USB sync item marked done

## [1.13.0] - 2026-10-23

### Added
- MPRIS2 desktop integration (Linux session bus) for media keys / shell widgets (`VOXPLAYER_DISABLE_MPRIS=1` to opt out)
- Localhost HTTP control daemon on `127.0.0.1:17890` (`/status`, `/play`, `/pause`, `/next`, `/volume`, `/seek`, `/open`); LAN bind requires `VOXPLAYER_DAEMON_ALLOW_LAN=1`
- Podcasts: subscribe to RSS/Atom feeds, refresh, download episodes into `~/.cache/voxplayer/podcasts/` (Media → Podcasts)
- Subtitle expansion: WebVTT + ASS/SSA sidecars (native libvlc file bind preferred for ASS; overlay for SRT/VTT)

### Changed
- ROADMAP Next items for daemon/MPRIS, podcast subscribe/download, and subtitle expansion marked done

## [1.12.0] - 2026-10-23

### Added
- Watch-folder library roots via `QFileSystemWatcher` + debounced incremental re-scan (native `vox_scan` / Zig when built); fingerprints in `~/.cache/voxplayer/library_index.json`
- Periodic 60s catch-up poll for nested directory changes
- Deeper browse facets: Album; Recently / Never / Most played (local play counts + last played)
- Play stats recorded on play; facets refresh accordingly

### Changed
- ROADMAP library watch/incremental and deeper facets marked done

## [1.11.0] - 2026-10-23

### Added
- Wayland embed path: force X11/XWayland when `DISPLAY` is set; probe future `libvlc_media_player_set_wayland_surface`; skip XID bind on pure Wayland without that API; clearer embed status copy (`VOXPLAYER_EMBED` / `VOXPLAYER_FORCE_WAYLAND`)
- Safer torrent startup buffers (smaller audio/video bases, soft caps, env overrides `VOXPLAYER_TORRENT_BUFFER_MB` / `_PCT`); re-assert sequential + first/last piece priority
- First-run qBittorrent Web UI setup guide (Media → Torrent → Web UI Setup Guide) with no embedded secrets; connection errors reuse the same copy

### Changed
- ROADMAP Wayland embed, torrent buffer, and first-run Web UI items marked done

## [1.10.0] - 2026-10-23

### Added
- Native engine hooks `MediaPlayerEncounteredError` and Error-state polling with clear, once-per-source messages (file name, extension, libvlc errmsg)
- Playback error dialogs state explicitly that VoxPlayer never switches to another media stack

### Changed
- Ended vs Error states are distinguished in the engine poll loop (Error is no longer a quiet stop)
- ROADMAP codec-error surfacing marked done

## [1.9.0] - 2026-10-23

### Added
- Bundled theme palettes (Ember, Midnight, Slate, Graphite) via View → Theme
- User theme packs as JSON under `~/.config/voxplayer/themes/` (example Ocean pack written on first list)
- Stronger empty-library panel with next actions and supported-format hints
- Clear unsupported-format dialogs for Open / drop / empty folder, plus codec-oriented engine errors

### Changed
- Legacy `theme=dark|light` settings migrate to Ember
- ROADMAP shell-polish theme + empty/unsupported items marked done

### Fixed
- Theme work no longer breaks window launch (`COLORS` import required by shell chrome)

## [1.8.0] - 2026-10-23

### Added
- Persist Open Folder library roots across sessions (re-indexed on launch)
- Transport shuffle + repeat (off / all / one), with wrap and shuffled Up next order

### Changed
- ROADMAP shell-polish items for roots and shuffle/repeat marked done

## [1.7.0] - 2026-10-23

### Added
- Native Phase 5: hardened in-app video WID embed (soft rebind on show/resize; hard only when the Qt native window is recreated)
- Coalesced non-blocking seeks with bounded Opening/Buffering retries; scrub uses fractional position, release uses exact time

### Changed
- ROADMAP Phase 5 marked done; Phase 4 (PyQt6 shell-only) remains ongoing

## [1.6.0] - 2026-10-23

### Added
- Native Phase 3: Zig alternate folder scanner (`native/vox_scan_zig`) with the same C ABI as Rust `vox_scan`
- Python loader prefers the Zig shared library when present (~2.7× smaller than the Rust scanner on Linux)

### Changed
- ROADMAP Phase 3 marked done; Phase 5 (WID embed harden) is next

## [1.5.0] - 2026-10-23

### Added
- Native Phase 2: Rust `vox_meta` worker pool for off-UI-thread tags (ffprobe) and thumbnails (ffmpeg), queued from Python with C callbacks
- Library home/facets/favorites queue missing covers via the pool (non-blocking); sync Python fallback when the cdylib is absent
- `voxplayer/native_workers.py` bridge for the Python shell

### Changed
- ROADMAP Phase 2 marked done; Phase 3 (optional Zig) is next

## [1.4.0] - 2026-10-23

### Changed
- Playback engine rewritten onto the native C media core (python-vlc + system libvlc) with in-app window-ID video embed
- Volume 0–200% via core volume / media gain; install guidance and docs retargeted to the new engine

### Fixed
- Black / missing in-app video stage caused by unreliable prior embed path
- Play/pause race on load that left media stopped after open

## [1.3.3] - 2026-10-23

### Fixed
- In-app video embed: do not open an external video window; bind WID before loading video
- Seek scrubbing no longer freezes the UI on large jumps (deferred keyframe seek; exact on release)
- Torrent picker: select multiple files across folders; ROADMAP scrub of excluded-scope wording

### Changed
- ROADMAP: stronger native Rust/C/Zig migration stance for long-run performance

## [1.3.2] - 2026-10-23

### Fixed
- Volume **0%** no longer snaps back to 100% (`volume or 100` truthiness on engine setup; play-start timers re-assert engine volume instead of clobbering a fresh 0% set)
- Persisted 0% survives reload; mute and 100–200% restore from 0% unchanged

### Tests
- `tests/test_volume_zero.py` — UI `set_volume(0)` + native engine readback across play-start timers

## [1.3.1] - 2026-10-23

### Fixed
- native-engine startup segfault under non-C locales (`LC_NUMERIC=C` before engine init)
- Native-engine install dialog no longer cites third-party GitHub installation URLs

## [1.3.0] - 2026-10-23

### Added
- **Zone-aware drag-and-drop**: drop on Home/library grid → **index only**; drop on Now Playing / Up next / bottom transport → **add and play immediately**
- **Rust `vox_scan` native scanner** (`native/vox_scan`) with Python ctypes loader for parallel folder walks; Python walker remains if the `.so` is not built
- Clear **native-engine install guidance** on Linux / Windows / macOS when python-vlc or system libvlc is missing (`run.py` preflight + startup dialog)

### Changed
- **Native C media core is the only playback engine** — Qt Multimedia is no longer a playback fallback (PyQt6 remains the UI shell; `QVideoWidget` is an embed surface only)
- Volume **0–200%** and mute use engine-native native-engine properties only (no Pulse/`pactl` design path)
- Filter tabs **All / Video / Audio / Recent** use understated icon+text controls instead of heavy filled chips
- Home library and Up next **scrollbars** are wider, higher-contrast, and easier to grab on the dark theme
- Default logical volume for new installs is **100%**; engine label always reports native C core (embedded or audio path)
- ROADMAP expanded: native Rust/Zig/C phases, skin/daemon/podcast-like feeds, portable-player concepts, Android/GrapheneOS — without third-party brand names

### Fixed
- Volume slider and speaker mute fighting each other when the engine was on the old Qt path
- `run.py` ensuring the project `.venv` (with `python-vlc`) is the interpreter users actually launch

### Removed
- Silent fallback from the native engine failures to Qt Multimedia playback
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
- **Native C media core is the default engine** when available — reliable 0–200% volume without requiring `VOXPLAYER_ENGINE` or Pulse-only workarounds for the happy path
- **Audio no longer opens the empty center stage**; video stage shows for video playback or when the user expands Now Playing
- `qbittorrent-api` and `python-vlc` moved into **main install dependencies**
- Up next lives in the Now Playing rail

### Fixed
- Video poster/thumbnail capture skips near-black frames and retries multiple seek points
- Torrent import no longer fails with “qbittorrent-api not available” on a normal `pip install voxplayer`

## [1.1.1] - 2026-10-22

### Fixed
- **Volume accuracy**: Media Information reports the same 0–200% logical volume as the transport slider (no longer Qt’s clamped 0–100%)
- **Volume boost**: Qt path applies PipeWire/PulseAudio per-stream gain above 100%; native C core uses volume 0–200
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
- **Playback engine abstraction** with Qt Multimedia default and optional native C media core (`pip install "voxplayer[native]"`)
- Hardware-decode hints for Qt FFmpeg (`QT_FFMPEG_DECODING_HW_DEVICE_TYPES`) and native-engine hardware decode when embedded

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
