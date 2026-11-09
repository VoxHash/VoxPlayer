#!/usr/bin/env bash
# Remove the installed VoxPlayer.app (Finder-style uninstall helper).
set -euo pipefail

TARGETS=(
  "/Applications/VoxPlayer.app"
  "$HOME/Applications/VoxPlayer.app"
)

removed=0
for app in "${TARGETS[@]}"; do
  if [[ -d "$app" ]]; then
    echo "Removing $app"
    rm -rf "$app"
    removed=1
  fi
done

# Optional user caches / preferences written by the app
for path in \
  "$HOME/Library/Caches/com.voxhash.voxplayer" \
  "$HOME/Library/Preferences/com.voxhash.voxplayer.plist" \
  "$HOME/Library/Application Support/VoxPlayer"
do
  if [[ -e "$path" ]]; then
    echo "Removing $path"
    rm -rf "$path"
  fi
done

if [[ "$removed" -eq 0 ]]; then
  echo "VoxPlayer.app not found in /Applications or ~/Applications"
  exit 1
fi

echo "VoxPlayer uninstalled."
