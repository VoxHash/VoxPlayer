#!/usr/bin/env python3
"""Stage native_core and prove libvlc loads from the bundle alone (no system lib paths).

Simulates ``pacman -Rns vlc`` / removing distro libvlc by restricting the FFI
candidate list to the staged tree. System libc/dbus remain (expected).
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    from pathlib import Path
    import importlib.util

    from voxplayer.native_core_paths import BUNDLE_DIRNAME, validate_native_core

    stage_path = Path(ROOT) / "packaging" / "stage_native_core.py"
    spec = importlib.util.spec_from_file_location("vox_stage_native_core", stage_path)
    if spec is None or spec.loader is None:
        print(f"FAIL cannot load {stage_path}")
        return 1
    stage_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage_mod)
    stage_native_core = stage_mod.stage_native_core

    dest = Path(ROOT) / BUNDLE_DIRNAME
    print(f"Staging → {dest}")
    manifest = stage_native_core(dest, force=True)
    print("validation:", manifest.get("validation"))

    report = validate_native_core(dest)
    if not report.get("ok"):
        print("FAIL validate:", report.get("errors"))
        return 1
    print(f"OK validate plugin_files={report.get('plugin_files')} lib={report.get('lib')}")

    lib = Path(str(report["lib"]))
    plugins = Path(str(report["plugins"]))

    # Restrict environment to the staged tree (ignore /usr/lib/libvlc).
    os.environ["VOXPLAYER_NATIVE_CORE"] = str(dest)
    os.environ["VOXPLAYER_LIBVLC"] = str(lib)
    os.environ["PYTHON_VLC_LIB_PATH"] = str(lib)
    os.environ["VLC_PLUGIN_PATH"] = str(plugins)
    os.environ["PYTHON_VLC_MODULE_PATH"] = str(plugins)
    # Prefer staged dir for libvlccore resolution
    prev_ld = os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["LD_LIBRARY_PATH"] = str(dest) + (os.pathsep + prev_ld if prev_ld else "")

    from voxplayer.engine import libvlc_ffi

    libvlc_ffi._LIB = None
    staged_only = [str(lib)]

    def _candidates_bundle_only():
        return list(staged_only)

    libvlc_ffi._candidate_lib_paths = _candidates_bundle_only  # type: ignore[assignment]

    try:
        ver = libvlc_ffi.probe()
    except Exception as exc:
        print(f"FAIL bundle-only libvlc load: {exc}")
        return 1
    print(f"OK bundle-only libvlc probe: {ver}")

    from voxplayer.engine.playback import require_vlc_module
    from voxplayer import native_core_paths as ncp

    args = ["--intf=dummy", "--quiet", "--no-video-title-show", "--no-stats"]
    args.extend(ncp.plugin_path_args())
    vlc = require_vlc_module()
    try:
        inst = vlc.Instance(*args)
        player = inst.media_player_new()
        player.audio_set_volume(40)
        player.release()
        inst.release()
    except Exception as exc:
        print(f"FAIL Instance from staged core: {exc}")
        return 1
    print("OK Instance + MediaPlayer from staged native_core (system lib paths ignored)")
    print("E2E NATIVE_CORE BUNDLE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
