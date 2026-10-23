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
try:
    import vlc
    print("OK: libvlc", vlc.libvlc_get_version())
except Exception as exc:
    print("libvlc installed; python-vlc binding:", exc)
    print("If needed: pip install python-vlc")
PY

echo ""
echo "Native C media core install finished."
