#!/usr/bin/env python3
"""Headless e2e smoke: version, window, engine, daemon, native scan, plugins."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("VOXPLAYER_DAEMON_PORT", "17999")
# Isolate QSettings from the user's daily profile during smoke
os.environ.setdefault("XDG_CONFIG_HOME", tempfile.mkdtemp(prefix="voxplayer-e2e-cfg-"))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _ok(msg: str) -> None:
    print(f"OK  {msg}")


def _fail(msg: str) -> None:
    print(f"FAIL {msg}")
    raise SystemExit(1)


def main() -> int:
    from voxplayer import __version__

    if __version__ != "1.47.0":
        _fail(f"package __version__ is {__version__!r}, expected 1.47.0")
    _ok(f"package version {__version__}")

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer

    from voxplayer.app import VoxPlayerMainWindow
    from voxplayer.daemon_client import DaemonClient
    from voxplayer.native_scan import (
        has_meta_scan,
        load_library,
        scan_media_dir_meta,
        backend_name,
    )
    from voxplayer.engine.playback import require_vlc_module
    from voxplayer import plugins as plugins_mod

    require_vlc_module()
    _ok("native C media core import")

    app = QApplication(sys.argv)
    win = VoxPlayerMainWindow()
    if win.current_version != __version__:
        _fail(
            f"About/UI current_version={win.current_version!r} "
            f"!= package {__version__!r}"
        )
    _ok(f"main window current_version={win.current_version}")

    if not getattr(win, "engine", None):
        _fail("playback engine missing")
    _ok(f"playback engine ready ({getattr(win.engine, 'backend', None)})")

    # Control daemon
    deadline = time.time() + 3.0
    client = DaemonClient("http://127.0.0.1:17999")
    status = {}
    while time.time() < deadline:
        status = client.status()
        if status.get("version") or status.get("ok") is not False:
            if "error" not in status or status.get("version"):
                break
        time.sleep(0.1)
    if status.get("version") != __version__:
        _fail(f"daemon /status version={status!r}")
    _ok(f"daemon status version={status.get('version')}")

    # Native scan (optional but expected on this machine)
    load_library()
    if has_meta_scan():
        td = tempfile.mkdtemp(prefix="vox-e2e-media-")
        sample = os.path.join(td, "tone.mp3")
        with open(sample, "wb") as fh:
            fh.write(b"ID3")
        meta = scan_media_dir_meta(td, [".mp3"])
        abs_sample = os.path.abspath(sample)
        if abs_sample not in (meta or {}):
            _fail(f"native meta scan missed sample: {meta}")
        _ok(f"native meta scan via {backend_name()}")
    else:
        print("WARN native meta scan unavailable (optional)")

    if not plugins_mod.plugins_enabled():
        _fail("plugins unexpectedly disabled")
    plugins_mod.ensure_example_plugin()
    _ok(f"plugins dir {plugins_mod.plugins_dir()}")

    # Transport / volume APIs without needing real media decode
    win.set_volume(42)
    if int(win.app_state.volume) != 42:
        _fail(f"set_volume failed: {win.app_state.volume}")
    _ok("volume set/get")

    # Open a tiny media file through the daemon open path (engine accepts path)
    td2 = tempfile.mkdtemp(prefix="vox-e2e-open-")
    # Generate a real short wav via ffmpeg if available; else skip open
    wav = os.path.join(td2, "beep.wav")
    rc = os.system(
        f"ffmpeg -y -hide_banner -loglevel error -f lavfi -i "
        f'"sine=frequency=440:duration=0.3" -ac 1 {wav!s} >/dev/null 2>&1'
    )
    if rc == 0 and os.path.isfile(wav):
        opened = client.open_path(wav)
        if not opened.get("ok", True) and opened.get("error"):
            _fail(f"daemon open failed: {opened}")
        time.sleep(0.4)
        st2 = client.status()
        if not st2.get("path"):
            _fail(f"daemon status missing path after open: {st2}")
        _ok(f"daemon open+status path={os.path.basename(st2.get('path') or '')}")
        client.playpause()
        client.stop()
        _ok("daemon playpause/stop")
    else:
        print("WARN ffmpeg unavailable; skipped media open e2e")

    # UI served
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:17999/ui/", timeout=2) as resp:
            body = resp.read()
            if b"VoxPlayer" not in body:
                _fail("daemon /ui missing branding")
        _ok("daemon /ui")
    except Exception as exc:
        _fail(f"daemon /ui: {exc}")

    # Pump Qt briefly then shut down
    QTimer.singleShot(200, app.quit)
    app.exec()
    try:
        win.control_daemon.stop()
    except Exception:
        pass
    _ok("clean shutdown")
    print("E2E PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
