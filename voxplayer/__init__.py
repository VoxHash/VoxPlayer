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
- SRT subtitle support
- Timeline preview and keyboard shortcuts

Author: VoxHash
License: MIT
Version: 1.0.1
"""

__version__ = "1.0.1"
__author__ = "VoxHash"
__email__ = "voxhash@example.com"
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
