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

## Control daemon remotes (TUI / browser)

With the desktop app running and the daemon enabled (default `127.0.0.1:17890`):

```bash
voxplayer-tui                 # interactive curses remote
voxplayer-ctl status          # one-shot JSON (alias of voxplayer-tui)
voxplayer-ctl playpause
voxplayer-ctl volume --percent 80
voxplayer-ctl seek --relative-ms 5000
voxplayer-ctl open --path /path/to/media.mp4
```

Browser remote (same JSON API; CORS enabled for external hosts / future WASM):

- Same-origin: open `http://127.0.0.1:17890/ui/` while the player is running
- Packaged files: `voxplayer/web_client/index.html` + `app.js`

Override target with `--url` or `VOXPLAYER_DAEMON_HOST` / `VOXPLAYER_DAEMON_PORT`.

## Useful environment flags

```bash
QT_QPA_PLATFORM=offscreen python test.py
QT_LOGGING_RULES='qt.multimedia.ffmpeg.debug=false' python app.py
```
