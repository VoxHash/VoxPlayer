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
| **python-mpv** + **system libmpv** | **Yes** | **Only** playback engine (volume 0–200%, mute) |
| `ffmpeg` | Recommended | Thumbnails / media inspection |
| qBittorrent + Web UI | Optional | Torrent streaming |
| Rust toolchain | Optional | Build `native/vox_scan` for faster folder scans |

**There is no Qt Multimedia playback fallback.** If libmpv is missing, VoxPlayer exits with install instructions.

### libmpv by platform

| Platform | Package / notes |
|----------|-----------------|
| Arch / Manjaro | `sudo pacman -S mpv` |
| Debian / Ubuntu | `sudo apt install libmpv2` (or `libmpv1` on older releases) |
| Fedora | `sudo dnf install mpv-libs` |
| macOS | `brew install mpv` |
| Windows | Install libmpv and ensure `mpv-2.dll` is on `PATH` |

Prefer **X11 / XWayland** for embedded video (`DISPLAY` set). On pure Wayland, audio volume still works; video embed may be limited.

## Method 2: From source (development)

```bash
git clone https://github.com/VoxHash/VoxPlayer.git
cd VoxPlayer
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py               # re-execs into .venv and preflights libmpv
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
.venv/bin/python -c "import mpv; p=mpv.MPV(vo='null', video='no', idle='yes'); p.terminate(); print('libmpv ok')"
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from voxplayer.engine.playback import require_mpv_module; require_mpv_module(); print('engine import ok')"
```
