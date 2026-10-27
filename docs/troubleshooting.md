# Troubleshooting

## App will not start / PyQt6 import errors

```bash
pip install -r requirements.txt
python -c "from PyQt6.QtWidgets import QApplication; print('ok')"
```

On Linux CI-like hosts, install OpenGL/EGL packages listed in `.github/workflows/ci.yml`.

## App exits: native engine / native C media core required

```bash
# FOSS path (no distro VLC required):
.venv/bin/pip install "voxplayer[libav]"
VOXPLAYER_DECODE=libav python run.py
# Or leave VOXPLAYER_DECODE unset — auto-falls back to libav if libvlc is missing

# libvlc path:
# Arch: sudo pacman -S vlc
# Debian/Ubuntu: sudo apt install vlc libvlc-dev
# Or: python packaging/stage_native_core.py --force
.venv/bin/python -c "from voxplayer.engine.decode_preflight import ensure_decode_backend; print(ensure_decode_backend())"
python run.py
```

## Volume or mute does nothing

- Confirm the Now Playing engine label shows **native C core** (not a missing-engine error)
- Volume is 0–200 via the native C media core; mute toggles `mute` without zeroing the slider
- Prefer X11/XWayland for video embed; audio volume still works on pure Wayland

## Black window or no video

- Confirm the file plays with the system media player or `ffplay`
- Prefer a session with `DISPLAY` (X11/XWayland) for embedded video
- Try another container (MP4 H.264 + AAC is a reliable baseline)
- On pure Wayland, audio may still play when embed is limited

## File not found

Missing paths show a **File Error** dialog. Pass an absolute path if the working directory differs from where you launched the app.

## Torrent: failed to connect / 403 Forbidden

1. Confirm qBittorrent Web UI is listening (`curl http://127.0.0.1:8080`)
2. Verify `QB_HOST`, `QB_USERNAME`, and `QB_PASSWORD`
3. After repeated bad logins, qBittorrent may ban your IP — restart the client or clear the ban, then retry with the correct password
4. Install the client library: `pip install qbittorrent-api`

## Torrent: no supported media file

The torrent must look like a media library: at least one supported audio/video extension and/or playlist (`.m3u`, `.cue`, etc.). ISO/distro/installer torrents are rejected before add. Multi-file media torrents prioritize a streamable file.

## Tests fail without a display

```bash
export QT_QPA_PLATFORM=offscreen
python test.py
```

## Unicode errors on Windows consoles

```bash
set PYTHONIOENCODING=utf-8
python test.py
```
