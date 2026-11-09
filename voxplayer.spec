# -*- mode: python ; coding: utf-8 -*-
"""Desktop bundle: PyQt6 shell + optional bundled native C media core (onedir / .app)."""

import sys
from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE

ROOT = Path(SPECPATH).resolve()
sys.path.insert(0, str(ROOT))

from voxplayer.native_core_paths import (  # noqa: E402
    BUNDLE_DIRNAME,
    discover_system_native_core,
    validate_native_core,
)

block_cipher = None
# macOS requires .icns; Windows uses .ico
if sys.platform == "darwin":
    icon = ROOT / "icon.icns"
    if not icon.is_file():
        icon = ROOT / "icon.ico"
else:
    icon = ROOT / "icon.ico"
entry = ROOT / "app.py"

# Prefer an already-staged native_core/ (arch-fixed) over live system discovery.
staged = ROOT / BUNDLE_DIRNAME
if staged.is_dir() and validate_native_core(staged).get("ok"):
    extra_binaries = []
    extra_datas = [(str(staged), BUNDLE_DIRNAME)]
    core_message = f"Using staged {staged}"
    core_found = True
else:
    core = discover_system_native_core()
    extra_binaries = list(core["binaries"])
    extra_datas = list(core["datas"])
    core_message = str(core["message"])
    core_found = bool(core["found"])

print("=== VoxPlayer packaging ===")
print(core_message)
if not core_found:
    print(
        "WARNING: native C media core not bundled — ship clear per-OS installers "
        "(packaging/install_native_core_*) or install system libvlc before build. "
        "Bundles still include FOSS libav when av is installed in the build env."
    )

datas = [
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "LICENSE"), "."),
]
if (ROOT / "voxplayer" / "logo.png").is_file():
    datas.append((str(ROOT / "voxplayer" / "logo.png"), "voxplayer"))
elif (ROOT / "logo.png").is_file():
    datas.append((str(ROOT / "logo.png"), "voxplayer"))
datas += extra_datas

hiddenimports = [
    "PyQt6",
    "qbittorrentapi",
    "voxplayer.engine.libvlc_ffi",
    "voxplayer.engine.libav_engine",
    "voxplayer.engine.decode_preflight",
    "av",
]

a = Analysis(
    [str(entry)],
    pathex=[str(ROOT)],
    binaries=extra_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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

# Proper Finder-installable .app on macOS (drag into /Applications).
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="VoxPlayer.app",
        icon=str(icon) if icon.is_file() else None,
        bundle_identifier="com.voxhash.voxplayer",
        info_plist={
            "CFBundleName": "VoxPlayer",
            "CFBundleDisplayName": "VoxPlayer",
            "CFBundleIdentifier": "com.voxhash.voxplayer",
            "CFBundleShortVersionString": "1.117.0",
            "CFBundleVersion": "1.117.0",
            "CFBundlePackageType": "APPL",
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeName": "Media File",
                    "CFBundleTypeRole": "Viewer",
                    "LSItemContentTypes": [
                        "public.movie",
                        "public.audio",
                        "public.mpeg-4",
                        "com.apple.quicktime-movie",
                    ],
                    "CFBundleTypeExtensions": [
                        "mp4",
                        "avi",
                        "mkv",
                        "mov",
                        "wmv",
                        "flv",
                        "webm",
                        "m4v",
                        "mp3",
                        "flac",
                        "wav",
                        "ogg",
                        "m4a",
                        "aac",
                        "wma",
                        "opus",
                    ],
                }
            ],
        },
    )
