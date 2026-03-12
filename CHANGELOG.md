# Changelog — VoxPlayer

All notable changes to VoxPlayer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Enhanced format support (HEVC, AV1, Opus)
- Audio equalizer with presets
- Playlist shuffle and repeat modes
- Plugin system architecture
- Cloud storage integration

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
