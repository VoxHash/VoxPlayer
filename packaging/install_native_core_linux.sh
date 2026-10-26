#!/usr/bin/env bash
# Clear per-OS installer: native C media core (libvlc) for Linux.
# Does not install VoxPlayer itself — only the playback dependency.
set -euo pipefail

echo "VoxPlayer — install native C media core (Linux)"
echo ""

if [[ "$(id -u)" -ne 0 ]]; then
  SUDO="${SUDO:-sudo}"
else
  SUDO=""
fi

if command -v pacman >/dev/null 2>&1; then
  $SUDO pacman -S --needed --noconfirm vlc
elif command -v apt-get >/dev/null 2>&1; then
  $SUDO apt-get update
  $SUDO apt-get install -y vlc libvlc-dev || $SUDO apt-get install -y vlc libvlc5
elif command -v dnf >/dev/null 2>&1; then
  $SUDO dnf install -y vlc
elif command -v zypper >/dev/null 2>&1; then
  $SUDO zypper install -y vlc
else
  echo "No supported package manager found."
  echo "Install the system libvlc / vlc package for your distro, then re-run VoxPlayer."
  exit 1
fi

python3 - <<'PY' || true
import sys
sys.path.insert(0, ".")
try:
    from voxplayer.engine import libvlc_ffi
    print("OK: libvlc", libvlc_ffi.probe())
except Exception as exc:
    print("libvlc package may be installed; Vox ctypes load failed:", exc)
    print("Ensure libvlc.so is on the linker path, then re-run from the VoxPlayer tree.")
PY

echo ""
echo "Native C media core install finished."
