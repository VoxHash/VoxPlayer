# CLI

## Launchers

```bash
python app.py
python app.py "/absolute/or/relative/path/to/media.mp4"
python run.py
voxplayer   # after pip install
```

`run.py` sets quieter Qt logging rules, then calls `app.main()`.

## Arguments

| Argument | Behavior |
|----------|----------|
| (none) | Open empty player window |
| `<media-path>` | If the file exists and the extension is supported, load it on startup |
| missing path | Warning on stderr; player still opens |
| unsupported extension | Warning on stderr; path ignored |

Torrent files (`.torrent`) are **not** accepted as the CLI media argument. Open them from the UI after configuring qBittorrent.

## Useful environment flags

```bash
QT_QPA_PLATFORM=offscreen python test.py
QT_LOGGING_RULES='qt.multimedia.ffmpeg.debug=false' python app.py
```
