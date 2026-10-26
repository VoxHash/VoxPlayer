#!/usr/bin/env python3
"""Stage a complete ``native_core/`` tree from the host system install.

Copies libvlc + libvlccore + helper libs + plugins so desktop e2e / bundles
can run without relying on distro package paths at runtime.

Usage::

    .venv/bin/python packaging/stage_native_core.py
    .venv/bin/python packaging/stage_native_core.py --dest /tmp/vox-native-core
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voxplayer.native_core_paths import (  # noqa: E402
    BUNDLE_DIRNAME,
    discover_system_native_core,
    validate_native_core,
)


def _copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    real = src.resolve() if src.exists() else src
    if not real.is_file():
        raise FileNotFoundError(f"missing source: {src}")
    shutil.copy2(real, dest)


def _stage_linux_symlink_aliases(dest_dir: Path, lib_basename: str) -> None:
    """Ensure ``libvlc.so`` / ``libvlc.so.5`` style names exist beside the real SONAME file."""
    # If we copied libvlc.so.5 already, also provide unversioned libvlc.so
    so5 = dest_dir / "libvlc.so.5"
    so = dest_dir / "libvlc.so"
    if so5.is_file() and not so.exists():
        try:
            so.symlink_to(so5.name)
        except OSError:
            shutil.copy2(so5, so)
    core9 = dest_dir / "libvlccore.so.9"
    core = dest_dir / "libvlccore.so"
    if core9.is_file() and not core.exists():
        try:
            core.symlink_to(core9.name)
        except OSError:
            shutil.copy2(core9, core)


def stage_native_core(dest: Path, *, force: bool = False) -> Dict[str, Any]:
    """Populate ``dest`` from ``discover_system_native_core()``. Returns manifest dict."""
    info = discover_system_native_core()
    if not info.get("found"):
        raise SystemExit(
            f"Cannot stage native_core: {info.get('message')}\n"
            "Install system libvlc / vlc first (packaging/install_native_core_*)."
        )

    if dest.exists() and force:
        # Keep tracked docs (README) when wiping staged binaries/plugins.
        keep_names = {"README.md", ".gitkeep"}
        for child in list(dest.iterdir()):
            if child.name in keep_names:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink(missing_ok=True)
    dest.mkdir(parents=True, exist_ok=True)

    copied_libs: List[str] = []
    seen: Set[str] = set()

    for src_s, dest_rel in info["binaries"]:  # type: ignore[union-attr]
        src = Path(str(src_s))
        # dest_rel is "native_core" — we stage into dest directly
        out_name = src.name
        # Prefer stable SONAME names when copying versioned files
        if out_name.startswith("libvlc.so.") and out_name != "libvlc.so.5":
            # Keep real file name AND ensure libvlc.so.5 points at content
            target = dest / out_name
            _copy_file(src, target)
            so5 = dest / "libvlc.so.5"
            if not so5.exists():
                shutil.copy2(target, so5)
            copied_libs.append(out_name)
            continue
        if out_name.startswith("libvlccore.so.") and out_name != "libvlccore.so.9":
            target = dest / out_name
            _copy_file(src, target)
            core9 = dest / "libvlccore.so.9"
            if not core9.exists():
                shutil.copy2(target, core9)
            copied_libs.append(out_name)
            continue
        key = src.resolve().as_posix() if src.exists() else str(src)
        if key in seen:
            continue
        seen.add(key)
        _copy_file(src, dest / out_name)
        copied_libs.append(out_name)

    plugins_src: Optional[Path] = None
    for src_s, _dest_rel in info["datas"]:  # type: ignore[union-attr]
        src = Path(str(src_s))
        if not src.is_dir():
            continue
        if (
            "plugin" in src.name.lower()
            or (src / "codec").is_dir()
            or (src / "demux").is_dir()
        ):
            plugins_src = src
            break
        plugins_src = src
        break

    plugins_dest = dest / "plugins"
    if plugins_src is not None and plugins_src.is_dir():
        if plugins_dest.exists():
            shutil.rmtree(plugins_dest)
        shutil.copytree(plugins_src, plugins_dest, symlinks=False)

    _stage_linux_symlink_aliases(dest, "libvlc.so.5")

    # Optional plugin cache (best-effort)
    cache_gen = Path("/usr/lib/vlc/vlc-cache-gen")
    if cache_gen.is_file() and plugins_dest.is_dir():
        try:
            import subprocess

            subprocess.run(
                [str(cache_gen), str(plugins_dest)],
                check=False,
                capture_output=True,
                timeout=60,
            )
        except Exception:
            pass

    report = validate_native_core(dest)
    manifest = {
        "version": 1,
        "source_message": info.get("message"),
        "dest": str(dest),
        "libs": sorted(set(copied_libs)),
        "plugins_dir": str(plugins_dest) if plugins_dest.is_dir() else None,
        "validation": report,
    }
    (dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if not report.get("ok"):
        raise SystemExit(
            "Staged native_core failed validation:\n"
            + "\n".join(f"  • {e}" for e in report.get("errors", []))
        )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage VoxPlayer native_core tree")
    parser.add_argument(
        "--dest",
        type=Path,
        default=ROOT / BUNDLE_DIRNAME,
        help=f"Destination directory (default: {ROOT / BUNDLE_DIRNAME})",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing dest")
    args = parser.parse_args()
    manifest = stage_native_core(args.dest, force=args.force)
    print(json.dumps(manifest, indent=2))
    print(f"OK staged native_core → {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
