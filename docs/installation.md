# Installation

## Method 1: PyPI (recommended)

```bash
pip install voxplayer
voxplayer
```

Optional torrent streaming extras:

```bash
pip install "voxplayer[torrent]"
```

Package: [https://pypi.org/project/voxplayer/](https://pypi.org/project/voxplayer/)

## System dependencies

| Dependency | Required? | Purpose |
|------------|-----------|---------|
| Python 3.8+ (3.10–3.12 recommended) | Yes | Runtime |
| PyQt6 / Qt Multimedia + FFmpeg backend | Yes (via pip) | UI and playback |
| `ffmpeg` | Recommended | Media inspection / platform codec support |
| qBittorrent + Web UI | Optional | Torrent streaming |
| `qbittorrent-api` | Optional | Python client for Web UI (`pip install "voxplayer[torrent]"`) |

On Debian/Ubuntu CI images, PyQt6 also needs OpenGL/EGL/XKB packages (see `.github/workflows/ci.yml`).

## Method 2: From source (development)

```bash
git clone https://github.com/VoxHash/VoxPlayer.git
cd VoxPlayer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Install torrent extras:

```bash
pip install -e ".[torrent]"
```

## Method 3: GitHub Releases

Download platform binaries from [Releases](https://github.com/VoxHash/VoxPlayer/releases) when published for your OS.

## Method 4: Python package build

```bash
pip install build
python -m build
pip install dist/voxplayer-*.whl
voxplayer
```

## Verify

```bash
QT_QPA_PLATFORM=offscreen python test.py
```
