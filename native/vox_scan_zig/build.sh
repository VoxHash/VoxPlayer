#!/usr/bin/env bash
# Build the Phase-3 Zig scanner and install next to Rust artifacts.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
if ! command -v zig >/dev/null 2>&1; then
  echo "zig not found — install Zig 0.14+ (e.g. https://ziglang.org/download/)" >&2
  exit 1
fi
cd "$ROOT"
zig build -Doptimize=ReleaseFast
mkdir -p "$REPO/native/target/zig-release"
cp -f "$ROOT/zig-out/lib/"libvox_scan_zig.* "$REPO/native/target/zig-release/" 2>/dev/null \
  || cp -f "$ROOT/zig-out/lib/libvox_scan_zig.so" "$REPO/native/target/zig-release/"
ls -la "$REPO/native/target/zig-release/"
if [[ -f "$REPO/native/target/release/libvox_scan.so" ]]; then
  echo "size compare:"
  wc -c "$REPO/native/target/release/libvox_scan.so" "$REPO/native/target/zig-release/libvox_scan_zig.so"
fi
