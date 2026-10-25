"""
VoxPlayer - A modern multimedia player built with PyQt6

A professional media player with advanced features including:
- Universal format support (MP4, AVI, MKV, MOV, WMV, FLV, WebM, MP3, FLAC, WAV, OGG, etc.)
- Ultra-compact design with maximum functionality
- True volume amplification up to 200%
- Professional file associations
- Advanced playlist management with drag & drop
- Torrent streaming support
- Auto-update system
- Fullscreen mode with auto-hiding controls
- SRT / WebVTT / ASS-SSA subtitle support; MPRIS2 + localhost control daemon; podcast feeds
- Portable / USB playlist and podcast sync
- LAN multi-room transport sync (peer control daemons)
- Gapless queue prefetch, bookmark resume, on-device library browse
- Albums / Artists / Tracks / Liked library navigation
- Optional spectrum / waveform transport chrome
- Broader HEVC / AV1 / Opus coverage via native core + codec probe
- Accessibility contrast pass + optional high-contrast mode
- Optional shell plugin hooks (out of the native core path)
- TUI + browser remotes for the localhost control daemon
- Desktop onedir bundles that can ship the native C media core
- Native parallel scan meta + quick content ids (Rust/Zig hot paths)
- Timeline preview and keyboard shortcuts
- Android / GrapheneOS LAN companion (library browse + remote control)
- LAN VPN bypass helper so companions reach the desktop daemon on Wi‑Fi/LAN
- On-device Media3 playback + Connect discovery for Android / Quest

Author: VoxHash
License: MIT
Version: 1.46.0
"""

__version__ = "1.46.0"
__author__ = "VoxHash Technologies"
__email__ = "contact@voxhash.dev"
__license__ = "MIT"
__description__ = "A modern multimedia player built with PyQt6"

# Import main classes for easy access
from .app import VoxPlayerMainWindow, main

__all__ = [
    "VoxPlayerMainWindow",
    "main",
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
]
