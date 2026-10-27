# FAQ

## Is VoxPlayer AI-powered?

No. It is a conventional PyQt6 media player with optional qBittorrent integration.

## Which platforms are supported?

Windows, macOS, and Linux. Source installs work wherever Python + PyQt6 run; packaged binaries depend on published GitHub Release assets.

## Do I need FFmpeg / the native media library installed separately?

**The native C media core (libvlc) is required** for playback (and for 0–200% volume / mute). Install via your OS package manager (`vlc` / libvlc). A system `ffmpeg` binary is useful for thumbnails and debugging but is not the playback engine.

## Why did the app refuse to start?

Usually no decode core is available. Install either FOSS libav (`pip install "voxplayer[libav]"`) or system/bundled libvlc, then `python run.py`. With libav installed, system VLC is optional (auto-fallback). There is no silent Qt Multimedia player fallback.

## Do I need another media player for debugging?

No. An alternate player is optional for comparing problem files.

## Why does opening a `.torrent` from the CLI not work?

The CLI argument path only accepts media extensions. Use **File → Open Torrent File** after configuring qBittorrent.

## Where are settings stored?

Platform Qt settings under organization `VoxHash` and application `VoxPlayer`.

## How do I report a vulnerability?

See [SECURITY.md](../SECURITY.md) and email contact@voxhash.dev.
