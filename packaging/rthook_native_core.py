"""PyInstaller runtime hook: activate bundled native C media core before imports."""

from voxplayer.native_core_paths import configure_bundled_native_core

configure_bundled_native_core()
