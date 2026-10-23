#!/usr/bin/env python3
"""Thin launcher — implementation lives in the voxplayer package."""

from voxplayer.app import VoxPlayerMainWindow, main, TorrentStreamer, UpdateChecker, Settings

__all__ = [
    "VoxPlayerMainWindow",
    "main",
    "TorrentStreamer",
    "UpdateChecker",
    "Settings",
]

if __name__ == "__main__":
    main()
