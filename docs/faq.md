# FAQ

## Is VoxPlayer AI-powered?

No. It is a conventional PyQt6 media player with optional qBittorrent integration.

## Which platforms are supported?

Windows, macOS, and Linux. Source installs work wherever Python + PyQt6 run; packaged binaries depend on published GitHub Release assets.

## Do I need FFmpeg installed separately?

Qt Multimedia ships with an FFmpeg backend on current PyQt6 wheels. A system `ffmpeg` binary is useful for debugging but is not required to launch the app.

## Do I need VLC?

No. VLC is optional for comparing problem files.

## Why does opening a `.torrent` from the CLI not work?

The CLI argument path only accepts media extensions. Use **File → Open Torrent File** after configuring qBittorrent.

## Where are settings stored?

Platform Qt settings under organization `VoxHash` and application `VoxPlayer`.

## How do I report a vulnerability?

See [SECURITY.md](../SECURITY.md) and email contact@voxhash.dev.
