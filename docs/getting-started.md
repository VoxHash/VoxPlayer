# Getting Started

## What you need

- Python 3.10+ recommended (3.8+ declared; CI covers 3.10–3.12)
- pip
- A desktop session with working audio/video output (PyQt6 multimedia uses FFmpeg)
- Optional for torrent streaming: [qBittorrent](https://www.qbittorrent.org/) with Web UI enabled

System utilities that help but are not required to launch the app:

- `ffmpeg` / `ffprobe` — inspect and convert media
- `vlc` — alternate playback for debugging problem files

## First run

```bash
git clone https://github.com/VoxHash/VoxPlayer.git
cd VoxPlayer
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open a file from the UI (**File → Open File(s)**) or pass a path:

```bash
python app.py "/path/to/video.mp4"
```

## Next steps

- [Installation](installation.md) for packaging options
- [Configuration](configuration.md) for settings and `QB_*` env vars
- [Quick Start](quick-start.md) for a minimal checklist
