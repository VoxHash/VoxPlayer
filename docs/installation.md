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
| **system / bundled libvlc** (Vox `libvlc_ffi`) | **Yes** | **Only** playback engine (volume 0–200%, mute) — no python-vlc |
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

## Method 3: GitHub Releases (desktop bundles)

Download platform archives from [Releases](https://github.com/VoxHash/VoxPlayer/releases) when published for your OS.

CI builds an **onedir** bundle via `voxplayer.spec` / `packaging/build_desktop.sh`. When the build host has the native C media core installed, it is copied under `native_core/` inside the bundle so target machines do not need a separate media-suite install.

| Artifact | Contents |
|----------|----------|
| `VoxPlayer-Linux.tar.gz` | `VoxPlayer/` onedir (Linux) |
| `VoxPlayer-Windows.zip` | `VoxPlayer/` onedir (Windows) |
| `VoxPlayer-macOS.zip` | `VoxPlayer/` onedir (macOS) |

Local build:

```bash
chmod +x packaging/build_desktop.sh
./packaging/build_desktop.sh
# → dist/VoxPlayer/VoxPlayer
```

### Clear per-OS installers (native core only)

If you use a pip install or a bundle built without `native_core/`, install the playback dependency with:

| Platform | Script |
|----------|--------|
| Linux | `packaging/install_native_core_linux.sh` |
| macOS | `packaging/install_native_core_macos.sh` |
| Windows | `packaging/install_native_core_windows.ps1` |

Debian/Ubuntu `.deb` builds (`build_debian.sh`) depend on `vlc | libvlc5` and wrap the onedir bundle.

## Method 4: Python package build

```bash
pip install build
python -m build
pip install dist/voxplayer-*.whl
voxplayer
```

## Verify

```bash
.venv/bin/python -c "from voxplayer.engine import libvlc_ffi; print('libvlc ok', libvlc_ffi.probe())"
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from voxplayer.engine.playback import require_vlc_module; require_vlc_module(); print('engine import ok')"
```
