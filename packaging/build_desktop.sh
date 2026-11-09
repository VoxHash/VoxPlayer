#!/usr/bin/env bash
# Build onedir desktop bundle with native C media core when available on the host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" && -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif [[ -z "$PYTHON" ]]; then
  PYTHON="python3"
fi

"$PYTHON" -m pip install -q -r requirements.txt "voxplayer[libav]" pyinstaller
"$PYTHON" -c "from voxplayer.native_core_paths import discover_system_native_core; print(discover_system_native_core()['message'])"
if "$PYTHON" -c "from voxplayer.native_core_paths import discover_system_native_core; import sys; sys.exit(0 if discover_system_native_core().get('found') else 1)"; then
  "$PYTHON" "$ROOT/packaging/stage_native_core.py" --force
  "$PYTHON" "$ROOT/scripts/e2e_native_core_bundle.py"
else
  echo "NOTE: skipping native_core stage (not found); libav fallback will be bundled when available."
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  exec "$ROOT/build_macos.sh"
fi

"$PYTHON" -m PyInstaller --clean --noconfirm voxplayer.spec

echo ""
echo "Bundle: $ROOT/dist/VoxPlayer/"
echo "Run:    $ROOT/dist/VoxPlayer/VoxPlayer"
ls -la "$ROOT/dist/VoxPlayer" | head -20
if [[ -d "$ROOT/dist/VoxPlayer/_internal/native_core" ]]; then
  echo "Bundled native_core: dist/VoxPlayer/_internal/native_core"
elif [[ -d "$ROOT/dist/VoxPlayer/native_core" ]]; then
  echo "Bundled native_core: dist/VoxPlayer/native_core"
else
  echo "NOTE: native_core folder missing — use packaging/install_native_core_* on target hosts."
fi
