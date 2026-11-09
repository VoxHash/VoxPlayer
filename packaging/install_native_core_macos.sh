#!/usr/bin/env bash
# Clear per-OS installer: native C media core for macOS (Homebrew cask / VLC.app).
# Prefers an architecture-matching VLC (arm64 on Apple Silicon, x86_64 on Intel).
set -euo pipefail

echo "VoxPlayer — install native C media core (macOS)"
echo ""

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script is for macOS only."
  exit 1
fi

HOST_ARCH="$(uname -m)"
echo "Host architecture: $HOST_ARCH"

vlc_arch() {
  local bin="$1"
  if [[ -x "$bin" ]]; then
    file -b "$bin" 2>/dev/null | tr ',' '\n' | head -1
  fi
}

have_matching_vlc=0
for candidate in \
  "$HOME/Applications/VLC.app/Contents/MacOS/VLC" \
  "/Applications/VLC.app/Contents/MacOS/VLC"
do
  if [[ -x "$candidate" ]]; then
    info="$(vlc_arch "$candidate" || true)"
    echo "Found $candidate ($info)"
    if echo "$info" | grep -qi "$HOST_ARCH"; then
      have_matching_vlc=1
    fi
  fi
done

if [[ "$have_matching_vlc" -eq 0 ]]; then
  if command -v brew >/dev/null 2>&1; then
    echo "Installing architecture-matching VLC via Homebrew cask…"
    # If an Intel-only /Applications/VLC.app blocks the cask, install into ~/Applications.
    if [[ -d /Applications/VLC.app ]] && ! file -b /Applications/VLC.app/Contents/MacOS/VLC | grep -qi "$HOST_ARCH"; then
      echo "Note: /Applications/VLC.app does not match $HOST_ARCH."
      echo "Installing a matching build into ~/Applications (no sudo)."
      brew fetch --cask vlc >/dev/null
      DMG="$(ls -t "$(brew --cache)"/downloads/*VLC*.dmg 2>/dev/null | head -1 || true)"
      if [[ -n "${DMG:-}" && -f "$DMG" ]]; then
        TMP="$(mktemp -d)"
        hdiutil attach "$DMG" -nobrowse -quiet -mountpoint "$TMP/mnt"
        mkdir -p "$HOME/Applications"
        rm -rf "$HOME/Applications/VLC.app"
        cp -R "$TMP/mnt/VLC.app" "$HOME/Applications/VLC.app"
        hdiutil detach "$TMP/mnt" -quiet || true
        rm -rf "$TMP"
      else
        brew install --cask vlc || true
      fi
    else
      brew install --cask vlc || brew install vlc || true
    fi
  else
    echo "Install Homebrew (https://brew.sh) then: brew install --cask vlc"
    echo "Or install a matching VLC.app from https://www.videolan.org/"
    exit 1
  fi
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" && -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

"$PYTHON" - <<'PY'
import sys
sys.path.insert(0, ".")
from voxplayer.native_core_paths import discover_system_native_core
info = discover_system_native_core()
print(info.get("message"))
if not info.get("found"):
    sys.exit(2)
from voxplayer.engine import libvlc_ffi
print("OK: libvlc", libvlc_ffi.probe())
PY

echo ""
echo "Native C media core install finished."
echo "Optional: .venv/bin/python packaging/stage_native_core.py --force"
