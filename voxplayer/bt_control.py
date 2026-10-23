"""Bluetooth RFCOMM control profile for Android / Quest companions (no GMS).

Uses the Linux ``AF_BLUETOOTH`` + ``BTPROTO_RFCOMM`` stdlib sockets (BlueZ).
Service UUID (SPP-compatible)::

    00001101-0000-1000-8000-00805f9b34fb

Default RFCOMM channel: ``5`` (``VOXPLAYER_BT_CHANNEL``). Optional SDP hint via
``sdptool`` when present.

Wire protocol: one JSON object per line (UTF-8), same command surface as the
HTTP daemon (``status``, ``playpause``, ``volume``, …) plus ``ping``.

Enable with ``VOXPLAYER_BT=1`` (default on when the adapter is available).
Disable with ``VOXPLAYER_BT=0``.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
from typing import Any, Callable, Dict, Optional


# Serial Port Profile UUID — Android createRfcommSocketToServiceRecord
SERVICE_UUID = "00001101-0000-1000-8000-00805f9b34fb"
SERVICE_NAME = "VoxPlayer Control"
DEFAULT_CHANNEL = 5


def bt_enabled() -> bool:
    raw = os.environ.get("VOXPLAYER_BT", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def bt_channel() -> int:
    try:
        return int(os.environ.get("VOXPLAYER_BT_CHANNEL", str(DEFAULT_CHANNEL)))
    except ValueError:
        return DEFAULT_CHANNEL


def _adapter_ready() -> bool:
    if not hasattr(socket, "AF_BLUETOOTH") or not hasattr(socket, "BTPROTO_RFCOMM"):
        return False
    try:
        out = subprocess.check_output(
            ["bluetoothctl", "show"], text=True, stderr=subprocess.DEVNULL, timeout=3
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return "Powered: yes" in out


def _ensure_adapter() -> bool:
    if _adapter_ready():
        _make_connectable()
        return True
    try:
        subprocess.run(["rfkill", "unblock", "bluetooth"], check=False, timeout=3)
        subprocess.run(
            ["bluetoothctl", "power", "on"],
            check=False,
            timeout=5,
            capture_output=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    ok = _adapter_ready()
    if ok:
        _make_connectable()
    return ok


def _make_connectable() -> None:
    """Allow already-paired phones to reconnect; brief discoverable for first pair."""
    for args in (
        ["bluetoothctl", "pairable", "on"],
        ["bluetoothctl", "discoverable", "on"],
    ):
        try:
            subprocess.run(args, check=False, timeout=5, capture_output=True)
        except (OSError, subprocess.TimeoutExpired):
            pass


def _local_adapter_address() -> str:
    """BlueZ RFCOMM bind needs a real BDADDR — empty string fails with EADDRNOTAVAIL."""
    try:
        out = subprocess.check_output(
            ["bluetoothctl", "list"], text=True, stderr=subprocess.DEVNULL, timeout=3
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        out = ""
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "Controller" and ":" in parts[1]:
            return parts[1]
    try:
        with open("/sys/class/bluetooth/hci0/address", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "00:00:00:00:00:00"


def _register_sdp(channel: int) -> None:
    """Best-effort Serial Port SDP record so phones can resolve the UUID."""
    sdptool = shutil.which("sdptool")
    if not sdptool:
        return
    try:
        subprocess.run(
            [sdptool, "add", f"--channel={channel}", "SP"],
            check=False,
            timeout=5,
            capture_output=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


class BluetoothControlServer:
    """Accept one RFCOMM client at a time; dispatch JSON line commands."""

    def __init__(self, dispatch: Callable[[str, Dict[str, Any]], Dict[str, Any]]):
        self._dispatch = dispatch
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.channel = bt_channel()
        self.address = ""
        self.active = False
        self.last_error = ""

    def start(self) -> bool:
        if not bt_enabled():
            self.last_error = "disabled"
            return False
        if not _ensure_adapter():
            self.last_error = "bluetooth adapter unavailable"
            return False
        if self._thread is not None:
            return True
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="voxplayer-bt-control", daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        t = self._thread
        self._thread = None
        self.active = False
        if t is not None:
            t.join(timeout=2.0)

    def _loop(self) -> None:
        channel = self.channel
        _register_sdp(channel)
        try:
            server = socket.socket(
                socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
            )
        except OSError as exc:
            self.last_error = str(exc)
            return
        bdaddr = _local_adapter_address()
        bind_errs: list[str] = []
        bound = False
        for candidate in (bdaddr, "00:00:00:00:00:00"):
            if not candidate:
                continue
            try:
                server.bind((candidate, channel))
                bound = True
                break
            except OSError as exc:
                bind_errs.append(f"{candidate}: {exc}")
        if not bound:
            self.last_error = "; ".join(bind_errs) or "bind failed"
            try:
                server.close()
            except OSError:
                pass
            return
        try:
            server.listen(1)
            server.settimeout(1.0)
            self.address = server.getsockname()[0]
            self.active = True
            self.last_error = ""
        except OSError as exc:
            self.last_error = str(exc)
            try:
                server.close()
            except OSError:
                pass
            return

        try:
            while not self._stop.is_set():
                try:
                    client, info = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    self._serve_client(client, info)
                finally:
                    try:
                        client.close()
                    except OSError:
                        pass
        finally:
            self.active = False
            try:
                server.close()
            except OSError:
                pass

    def _serve_client(self, client: socket.socket, info) -> None:
        client.settimeout(30.0)
        buf = b""
        # Hello line so the phone knows the profile is alive
        try:
            hello = {
                "ok": True,
                "service": "voxplayer-bt",
                "uuid": SERVICE_UUID,
                "channel": self.channel,
                "peer": list(info) if info else [],
            }
            client.sendall((json.dumps(hello) + "\n").encode("utf-8"))
        except OSError:
            return
        while not self._stop.is_set():
            try:
                chunk = client.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    req = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    resp = {"ok": False, "error": f"bad_json: {exc}"}
                else:
                    cmd = str(req.get("cmd") or req.get("action") or "").strip().lower()
                    if cmd == "ping":
                        resp = {"ok": True, "pong": True}
                    else:
                        try:
                            resp = self._dispatch(cmd, req if isinstance(req, dict) else {})
                            if not isinstance(resp, dict):
                                resp = {"ok": True}
                        except Exception as exc:
                            resp = {"ok": False, "error": str(exc)}
                try:
                    client.sendall((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
                except OSError:
                    return
