# Example 02 — Stream from a torrent file

## Goal

Add a `.torrent` through qBittorrent and let VoxPlayer stream a media file once buffered.

## Prerequisites

- qBittorrent running with Web UI on port 8080 (or your chosen port)
- Valid Web UI credentials
- Optional package: `pip install qbittorrent-api`

```bash
export QB_HOST=127.0.0.1:8080
export QB_USERNAME=admin
export QB_PASSWORD='your-webui-password'
pip install qbittorrent-api
python app.py
```

## Steps

1. In VoxPlayer, choose **File → Open Torrent File**
2. Select a torrent that contains playable video/audio
3. Wait for connection + sequential download progress
4. Playback begins when the selected media file reaches the buffer threshold

## Notes

- CLI `python app.py file.torrent` is **not** supported; torrents open from the UI
- Wrong credentials or a banned IP produce a **Torrent Error** dialog
- Keep torrent and download directories out of git (already covered by `.gitignore`)
