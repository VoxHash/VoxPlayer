# Quick Start

Install from PyPI:

```bash
pip install voxplayer
voxplayer "/path/to/video.mp4"
```

Or from a source clone (validated on Linux with a fresh virtualenv):

```bash
git clone https://github.com/VoxHash/VoxPlayer.git
cd VoxPlayer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python test.py
python app.py "/path/to/video.mp4"
```

Expected results:

1. `python test.py` prints `3/3 tests passed`
2. The window title becomes `<filename> - VoxPlayer`
3. Playback starts (or waits for Play / Space)

Optional torrent extras:

```bash
pip install "qbittorrent-api>=0.4.0"
export QB_HOST=127.0.0.1:8080
export QB_USERNAME=admin
export QB_PASSWORD='your-webui-password'
```

Then use **File → Open Torrent File** inside the app (qBittorrent must already be running with Web UI enabled).
