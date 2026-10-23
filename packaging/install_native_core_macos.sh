#!/usr/bin/env bash
# Clear per-OS installer: native C media core for macOS (Homebrew or VLC.app).
set -euo pipefail

echo "VoxPlayer — install native C media core (macOS)"
echo ""

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script is for macOS only."
  exit 1
fi

if command -v brew >/dev/null 2>&1; then
  brew install vlc
elif [[ -d "/Applications/VLC.app" ]]; then
  echo "VLC.app already present at /Applications/VLC.app"
else
  echo "Install Homebrew (https://brew.sh) then: brew install vlc"
  echo "Or install VLC.app from https://www.videolan.org/ and re-run."
  exit 1
fi

python3 - <<'PY' || true
try:
    import vlc
    print("OK: libvlc", vlc.libvlc_get_version())
except Exception as exc:
    print("Core present; python-vlc binding:", exc)
    print("If needed: pip install python-vlc")
PY

echo ""
echo "Native C media core install finished."
