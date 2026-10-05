# Troubleshooting

## App will not start / PyQt6 import errors

```bash
pip install -r requirements.txt
python -c "from PyQt6.QtWidgets import QApplication; print('ok')"
```

On Linux CI-like hosts, install OpenGL/EGL packages listed in `.github/workflows/ci.yml`.

## Black window or no video

- Confirm the file plays in VLC or `ffplay`
- Ensure codecs are available to Qt Multimedia / FFmpeg
- Try another container (MP4 H.264 + AAC is the most reliable baseline)

## File not found

Missing paths show a **File Error** dialog. Pass an absolute path if the working directory differs from where you launched the app.

## Torrent: failed to connect / 403 Forbidden

1. Confirm qBittorrent Web UI is listening (`curl http://127.0.0.1:8080`)
2. Verify `QB_HOST`, `QB_USERNAME`, and `QB_PASSWORD`
3. After repeated bad logins, qBittorrent may ban your IP — restart the client or clear the ban, then retry with the correct password
4. Install the client library: `pip install qbittorrent-api`

## Torrent: no supported media file

The torrent must contain at least one supported audio/video extension. Multi-file torrents prioritize streamable media.

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
