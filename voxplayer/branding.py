"""Ensure VoxPlayer shows as itself in the OS (mixer icon/name, desktop entry).

LibVLC's Pulse/PipeWire backend reads ``application.icon_name`` from
``Instance.set_app_id(..., icon)``. That name must resolve in the XDG icon theme
(``voxplayer``), otherwise panels fall back to the VLC cone.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


ICON_NAME = "voxplayer"
APP_ID = "dev.voxhash.voxplayer"


def package_logo_path() -> Path:
    return Path(__file__).resolve().parent / "logo.png"


def ensure_xdg_app_branding(version: str = "") -> Optional[Path]:
    """Install/refresh ``~/.local/share`` desktop entry + hicolor icon. Best-effort."""
    logo = package_logo_path()
    if not logo.is_file():
        return None
    home = Path.home()
    icon_dir = home / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    icon_dir.mkdir(parents=True, exist_ok=True)
    dest = icon_dir / f"{ICON_NAME}.png"
    try:
        # Always refresh so mixer picks up the current brand art
        shutil.copy2(logo, dest)
    except OSError:
        return None

    apps = home / ".local" / "share" / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    desktop = apps / f"{ICON_NAME}.desktop"
    exec_path = shutil.which("voxplayer") or "voxplayer"
    body = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Version={version or '1.0'}\n"
        "Name=VoxPlayer\n"
        "GenericName=Media Player\n"
        "Comment=Desktop media player (native C media core)\n"
        f"Exec={exec_path} %F\n"
        f"Icon={ICON_NAME}\n"
        "Terminal=false\n"
        "Categories=AudioVideo;Player;Audio;Video;\n"
        "StartupNotify=true\n"
        "StartupWMClass=VoxPlayer\n"
    )
    try:
        desktop.write_text(body, encoding="utf-8")
    except OSError:
        pass

    # Refresh icon cache so Pulse/GNOME see the new file immediately
    for cmd in (
        ["gtk-update-icon-cache", "-f", "-t", str(home / ".local" / "share" / "icons" / "hicolor")],
        ["xdg-icon-resource", "forceupdate"],
    ):
        try:
            subprocess.run(cmd, check=False, timeout=5, capture_output=True)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return dest
