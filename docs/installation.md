# Installation

## Method 1: PyPI (recommended)

```bash
pip install voxplayer
voxplayer
```

Package: [https://pypi.org/project/voxplayer/](https://pypi.org/project/voxplayer/)

## System dependencies

| Dependency | Required? | Purpose |
|------------|-----------|---------|
| Python 3.8+ (3.10–3.12 recommended) | Yes | Runtime |
| PyQt6 | Yes (via pip) | Desktop UI shell |
| **python-vlc** + **system libvlc** | **Yes** | **Only** playback engine (volume 0–200%, mute) |
| `ffmpeg` | Recommended | Thumbnails / media inspection |
| qBittorrent + Web UI | Optional | Torrent streaming |
| Rust toolchain | Optional | Build `native/vox_scan` for faster folder scans |

**There is no Qt Multimedia playback fallback.** If native C media core is missing, VoxPlayer exits with install instructions.

### Native C media core by platform

| Platform | Package / notes |
|----------|-----------------|
| Arch / Manjaro | `sudo pacman -S vlc` |
| Debian / Ubuntu | `sudo apt install vlc libvlc-dev` (or `libvlc` on older releases) |
| Fedora | `sudo dnf install vlc` |
| macOS | `brew install vlc` |
| Windows | Install the desktop media suite and ensure `libvlc.dll` is on `PATH` |

Prefer **X11 / XWayland** for embedded video (`DISPLAY` set). On pure Wayland, audio volume still works; video embed may be limited.

## Method 2: From source (development)

```bash
git clone https://github.com/VoxHash/VoxPlayer.git
cd VoxPlayer
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py               # re-execs into .venv and preflights the native C media core
```

Optional native scanner:

```bash
cargo build --release --manifest-path native/Cargo.toml
```

Optional metadata extras:

```bash
pip install -e ".[metadata]"
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
.venv/bin/python -c "import vlc; print('libvlc ok', vlc.libvlc_get_version())"
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from voxplayer.engine.playback import require_vlc_module; require_vlc_module(); print('engine import ok')"
```
