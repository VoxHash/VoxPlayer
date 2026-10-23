# -*- mode: python ; coding: utf-8 -*-
"""Desktop bundle: PyQt6 shell + optional bundled native C media core (onedir)."""

import sys
from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis

ROOT = Path(SPECPATH).resolve()
sys.path.insert(0, str(ROOT))

from voxplayer.native_core_paths import discover_system_native_core  # noqa: E402

block_cipher = None
icon = ROOT / "icon.ico"
entry = ROOT / "app.py"

core = discover_system_native_core()
extra_binaries = list(core["binaries"])
extra_datas = list(core["datas"])

print("=== VoxPlayer packaging ===")
print(core["message"])
if not core["found"]:
    print(
        "WARNING: native C media core not bundled — ship clear per-OS installers "
        "(packaging/install_native_core_*) or install system libvlc before build."
    )

datas = [
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "LICENSE"), "."),
]
if (ROOT / "voxplayer" / "logo.png").is_file():
    datas.append((str(ROOT / "voxplayer" / "logo.png"), "voxplayer"))
datas += extra_datas

a = Analysis(
    [str(entry)],
    pathex=[str(ROOT)],
    binaries=extra_binaries,
    datas=datas,
    hiddenimports=["vlc", "PyQt6", "qbittorrentapi"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "packaging" / "rthook_native_core.py")],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VoxPlayer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon) if icon.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VoxPlayer",
)
