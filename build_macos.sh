#!/usr/bin/env bash
# Build a Finder-installable VoxPlayer.app + DMG (no source tree required on target Mac).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

VERSION="$(python3 - <<'PY'
from pathlib import Path
text = Path("voxplayer/__init__.py").read_text(encoding="utf-8")
for line in text.splitlines():
    if line.startswith("__version__"):
        print(line.split("=", 1)[1].strip().strip("\"'"))
        break
else:
    print("0.0.0")
PY
)"

echo "========================================"
echo "VoxPlayer macOS App Builder (${VERSION})"
echo "========================================"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: This script must be run on macOS"
  exit 1
fi

PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" && -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif [[ -z "$PYTHON" ]]; then
  PYTHON="python3"
fi

echo "Using Python: $PYTHON ($("$PYTHON" --version 2>&1))"

"$PYTHON" -m pip install -q -U pip
"$PYTHON" -m pip install -q -r requirements.txt "voxplayer[libav]" pyinstaller pillow

# Ensure a macOS .icns exists for the Finder app icon
if [[ ! -f "$ROOT/icon.icns" && -f "$ROOT/logo.png" ]]; then
  echo "Generating icon.icns from logo.png…"
  ICONSET="$(mktemp -d)/VoxPlayer.iconset"
  mkdir -p "$ICONSET"
  for pair in "16:16" "32:16" "32:32" "64:32" "128:128" "256:128" "256:256" "512:256" "512:512" "1024:512"; do
    size="${pair%%:*}"; base="${pair##*:}"
    if [[ "$size" == "$base" ]]; then
      out="$ICONSET/icon_${base}x${base}.png"
    else
      out="$ICONSET/icon_${base}x${base}@2x.png"
    fi
    sips -z "$size" "$size" "$ROOT/logo.png" --out "$out" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o "$ROOT/icon.icns"
fi

# Stage arch-matching native_core when a usable VLC.app is present.
if "$PYTHON" -c "from pathlib import Path; from voxplayer.native_core_paths import validate_native_core; import sys; sys.exit(0 if validate_native_core(Path('native_core')).get('ok') else 1)"; then
  echo "Using existing staged native_core/"
elif "$PYTHON" -c "from voxplayer.native_core_paths import discover_system_native_core; import sys; sys.exit(0 if discover_system_native_core().get('found') else 1)"; then
  echo "Staging native_core from matching VLC install…"
  "$PYTHON" "$ROOT/packaging/stage_native_core.py" --force
  "$PYTHON" "$ROOT/scripts/e2e_native_core_bundle.py" || {
    echo "WARNING: staged native_core e2e failed — continuing with libav fallback in bundle"
  }
else
  echo "NOTE: no arch-matching VLC found — app will rely on bundled FOSS libav (PyAV)."
  echo "      Optional: brew install --cask vlc  (matching CPU) then re-run."
fi

rm -rf build dist/VoxPlayer dist/VoxPlayer.app "VoxPlayer-${VERSION}-macOS.dmg" VoxPlayer.app

echo "Building onedir + VoxPlayer.app via PyInstaller…"
"$PYTHON" -m PyInstaller --clean --noconfirm voxplayer.spec

APP_PATH=""
if [[ -d "$ROOT/dist/VoxPlayer.app" ]]; then
  APP_PATH="$ROOT/dist/VoxPlayer.app"
elif [[ -d "$ROOT/dist/VoxPlayer/VoxPlayer.app" ]]; then
  APP_PATH="$ROOT/dist/VoxPlayer/VoxPlayer.app"
fi

if [[ -z "$APP_PATH" ]]; then
  echo "ERROR: VoxPlayer.app was not produced by PyInstaller"
  ls -la "$ROOT/dist" || true
  exit 1
fi

# Ensure a drag-target copy at repo root for create-dmg / local install.
rm -rf "$ROOT/VoxPlayer.app"
cp -R "$APP_PATH" "$ROOT/VoxPlayer.app"

# Ad-hoc sign so Gatekeeper can open locally built apps more reliably.
if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "$ROOT/VoxPlayer.app" 2>/dev/null || true
fi

echo "App bundle: $ROOT/VoxPlayer.app"

if ! command -v create-dmg >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    brew install create-dmg
  else
    echo "WARNING: create-dmg missing — producing zip only"
  fi
fi

DMG_NAME="VoxPlayer-${VERSION}-macOS.dmg"
if command -v create-dmg >/dev/null 2>&1; then
  rm -f "$ROOT/$DMG_NAME"
  create-dmg \
    --volname "VoxPlayer" \
    --window-pos 200 120 \
    --window-size 640 360 \
    --icon-size 100 \
    --icon "VoxPlayer.app" 160 140 \
    --hide-extension "VoxPlayer.app" \
    --app-drop-link 460 140 \
    "$ROOT/$DMG_NAME" \
    "$ROOT/VoxPlayer.app" || {
      echo "create-dmg failed; falling back to zip"
      DMG_NAME=""
    }
fi

ZIP_NAME="VoxPlayer-${VERSION}-macOS.zip"
rm -f "$ROOT/dist/$ZIP_NAME"
ditto -c -k --sequesterRsrc --keepParent "$ROOT/VoxPlayer.app" "$ROOT/dist/$ZIP_NAME"

echo ""
echo "========================================"
echo "macOS build completed"
echo "========================================"
echo "Install (Finder): open the DMG and drag VoxPlayer to Applications"
[[ -n "$DMG_NAME" && -f "$ROOT/$DMG_NAME" ]] && echo "  DMG: $ROOT/$DMG_NAME"
echo "  APP: $ROOT/VoxPlayer.app"
echo "  ZIP: $ROOT/dist/$ZIP_NAME"
echo "Uninstall: drag VoxPlayer.app from Applications to Trash"
echo "  or: ./packaging/uninstall_macos_app.sh"
