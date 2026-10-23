"""USB helper: ensure a single adb server and reverse-forward the control daemon.

Multiple stray ``adb`` fork-servers (common with IDE plugins) steal USB devices
and break ``adb reverse``. Quest/Meta UsbFfs reverse can also flake; this tool
resets reverse and probes the daemon from the device with ``toybox nc``.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
from typing import List, Optional, Sequence


DEFAULT_PORT = 17890


def _adb_bin() -> str:
    return os.environ.get("ADB", shutil.which("adb") or "adb")


def _run(cmd: Sequence[str], timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(cmd),
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def kill_extra_adb_servers(*, keep_port: int = 5037) -> List[str]:
    """Kill every adb server except the one on keep_port (best-effort)."""
    notes: List[str] = []
    ps = _run(["ps", "-eo", "pid,args"])
    victims: List[str] = []
    for line in (ps.stdout or "").splitlines():
        if "adb" not in line or "fork-server" not in line:
            continue
        if f"tcp:{keep_port}" in line:
            continue
        pid = line.strip().split(None, 1)[0]
        if pid.isdigit():
            victims.append(pid)
    for pid in victims:
        _run(["kill", pid])
        notes.append(f"killed adb pid {pid}")
    # Also killall if still fragmented
    if victims:
        time.sleep(0.5)
    return notes


def ensure_single_server() -> None:
    kill_extra_adb_servers()
    _run([_adb_bin(), "start-server"])


def list_devices() -> List[dict]:
    ensure_single_server()
    cp = _run([_adb_bin(), "devices", "-l"])
    rows: List[dict] = []
    for line in (cp.stdout or "").splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2 or parts[1] != "device":
            continue
        serial = parts[0]
        meta = {"serial": serial, "state": parts[1]}
        for p in parts[2:]:
            if ":" in p:
                k, v = p.split(":", 1)
                meta[k] = v
        rows.append(meta)
    return rows


def setup_reverse(serial: str, port: int = DEFAULT_PORT) -> bool:
    adb = _adb_bin()
    _run([adb, "-s", serial, "reverse", "--remove-all"])
    cp = _run([adb, "-s", serial, "reverse", f"tcp:{port}", f"tcp:{port}"])
    return cp.returncode == 0


def probe_daemon_via_device(serial: str, port: int = DEFAULT_PORT) -> Optional[dict]:
    """GET /status through device localhost (adb reverse).

    Prefer a pushed static ``/data/local/tmp/curl`` (toybox ``nc`` often returns
    empty on Quest/Pixel UsbFfs reverse). Fall back to nc + base64 request.
    """
    curl_probe = (
        f"if [ -x /data/local/tmp/curl ]; then "
        f"/data/local/tmp/curl -sS -m 5 http://127.0.0.1:{port}/status; "
        f"else echo NOCURL; fi"
    )
    cp = _run([_adb_bin(), "-s", serial, "shell", curl_probe], timeout=20)
    out = (cp.stdout or "").strip()
    if out and out != "NOCURL" and "{" in out:
        body = out[out.find("{") : out.rfind("}") + 1]
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass
    req = f"GET /status HTTP/1.0\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
    b64 = base64.b64encode(req.encode()).decode()
    script = (
        f"echo {b64} | toybox base64 -d | toybox nc -w 3 -W 5 127.0.0.1 {port} "
        f"> /data/local/tmp/vox_daemon_probe.txt; "
        f"toybox cat /data/local/tmp/vox_daemon_probe.txt"
    )
    cp = _run([_adb_bin(), "-s", serial, "shell", script], timeout=20)
    out = (cp.stdout or "") + (cp.stderr or "")
    if "{" not in out:
        return None
    body = out[out.find("{") : out.rfind("}") + 1]
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="voxplayer-usb-bridge")
    p.add_argument("command", nargs="?", default="status", choices=("status", "reset", "probe"))
    p.add_argument("--serial", default="", help="Device serial (default: all)")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(list(argv) if argv is not None else None)

    if args.command == "reset":
        notes = kill_extra_adb_servers()
        ensure_single_server()
        devices = list_devices()
        results = []
        for d in devices:
            if args.serial and d["serial"] != args.serial:
                continue
            ok = setup_reverse(d["serial"], args.port)
            results.append({"serial": d["serial"], "model": d.get("model"), "reverse": ok})
        payload = {"notes": notes, "devices": results}
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0

    if args.command == "probe":
        devices = list_devices()
        rows = []
        for d in devices:
            if args.serial and d["serial"] != args.serial:
                continue
            setup_reverse(d["serial"], args.port)
            st = probe_daemon_via_device(d["serial"], args.port)
            rows.append(
                {
                    "serial": d["serial"],
                    "model": d.get("model"),
                    "status": st,
                    "ok": bool(st and "version" in st),
                }
            )
        print(json.dumps(rows, indent=2) if args.json else rows)
        return 0 if all(r["ok"] for r in rows if rows) else 1

    # status
    devices = list_devices()
    print(json.dumps(devices, indent=2) if args.json else "\n".join(
        f"{d['serial']}\t{d.get('model','?')}\t{d.get('device','?')}" for d in devices
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
