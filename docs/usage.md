# Usage

## Open media

- **UI:** File → Open File(s) / Open Folder
- **CLI:** `python app.py "/path/to/video.mp4"`
- **Drag & drop:** Drop files or folders onto the window
- **Associations (Windows):** run `register_file_associations.bat` as Administrator

Supported extensions include MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V, MP3, FLAC, WAV, OGG, M4A, AAC, WMA.

## Playlist

- Add files via menu or drag & drop
- Filter with the search box
- Import/export M3U, PLS, XSPF from the File menu

## Playback controls

| Shortcut | Action |
|----------|--------|
| `Space` | Play / Pause |
| `Left` / `Right` | Seek |
| `Up` / `Down` | Volume |
| `M` | Mute |
| `F11` | Fullscreen |
| `Ctrl+O` | Open file(s) |
| `Ctrl+L` | Toggle playlist |
| `Ctrl+Q` | Quit |

## Torrent streaming

Requires a running qBittorrent Web UI and valid `QB_*` env vars (see [configuration](configuration.md)).

1. File → Open Torrent File (or Open Magnet Link)
2. Wait for sequential buffer thresholds
3. Playback starts when a supported media file inside the torrent is ready

## Error handling

- Missing local paths show a **File Error** dialog and do not crash
- Unsupported CLI extensions print a warning and launch without a file
- Torrent failures surface as **Torrent Error** dialogs (connection, auth, missing media)
