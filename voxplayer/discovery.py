"""LAN discovery beacon so Android / Quest companions find the desktop without USB.

Broadcasts a small JSON announce on UDP ``17891`` (override with
``VOXPLAYER_DISCOVERY_PORT``). Companions listen and may send a probe
``VOXPLAYER_DISCOVER?``; the desktop replies with a unicast announce.

Wi‑Fi is the supported Connect transport (same LAN). Bluetooth does not carry
the HTTP control API without a custom profile — the Connect UI steers users to
Wi‑Fi / LAN (and ``voxplayer-lan-bypass`` when a VPN steals RFC1918 routes).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
from typing import Optional


DEFAULT_DISCOVERY_PORT = 17891
PROBE = b"VOXPLAYER_DISCOVER?"


def discovery_enabled() -> bool:
    raw = os.environ.get("VOXPLAYER_DISCOVERY", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def discovery_port() -> int:
    try:
        return int(os.environ.get("VOXPLAYER_DISCOVERY_PORT", str(DEFAULT_DISCOVERY_PORT)))
    except ValueError:
        return DEFAULT_DISCOVERY_PORT


def _iface_ipv4s() -> list:
    rows = []
    try:
        out = subprocess.check_output(
            ["ip", "-4", "-o", "addr", "show", "up"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return rows
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 4 or "inet" not in parts:
            continue
        iface = parts[1].split("@", 1)[0]
        cidr = parts[parts.index("inet") + 1]
        ip = cidr.split("/", 1)[0]
        rows.append((iface, ip))
    return rows


def _is_vpn_iface(name: str) -> bool:
    n = (name or "").lower()
    return (
        n.startswith("proton")
        or n.startswith("wg")
        or n.startswith("tun")
        or n.startswith("tailscale")
        or n.startswith("nordlynx")
        or n.startswith("pvpn")
        or n.startswith("zt")
    )


def _is_lan_iface(name: str) -> bool:
    n = (name or "").lower()
    if _is_vpn_iface(n) or n == "lo":
        return False
    if n.startswith(("br-", "docker", "veth", "virbr", "libvirt")):
        return False
    return n.startswith(("en", "eth", "wl", "wlan", "usb", "rndis", "mac"))


def _local_ipv4s() -> list:
    preferred: list = []
    for iface, ip in _iface_ipv4s():
        if not ip or ip.startswith("127."):
            continue
        if _is_lan_iface(iface) and ip not in preferred:
            preferred.append(ip)
    if not preferred:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                preferred.append(ip)
        except OSError:
            pass
    return preferred


class DiscoveryBeacon:
    """UDP announce + probe responder for companion Connect discovery."""

    def __init__(self, http_host: str, http_port: int, version: str = "", name: str = "VoxPlayer"):
        self.http_host = http_host
        self.http_port = int(http_port)
        self.version = version or ""
        self.name = name or "VoxPlayer"
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.port = discovery_port()

    def _payload(self, lan_ip: str) -> bytes:
        body = {
            "service": "voxplayer",
            "name": self.name,
            "host": lan_ip,
            "port": self.http_port,
            "version": self.version,
            "api": "http",
        }
        return json.dumps(body, separators=(",", ":")).encode("utf-8")

    def _announce_targets(self, lan_ips: list) -> list:
        targets = [("255.255.255.255", self.port)]
        for ip in lan_ips:
            parts = ip.split(".")
            if len(parts) == 4:
                targets.append((f"{parts[0]}.{parts[1]}.{parts[2]}.255", self.port))
        seen = set()
        out = []
        for t in targets:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out

    def _loop(self) -> None:
        # Separate listen + announce sockets so our own broadcasts do not fill Recv-Q.
        listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        announce = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listen.bind(("0.0.0.0", self.port))
            listen.settimeout(0.5)
            announce.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            announce.settimeout(0.5)
        except OSError:
            try:
                listen.close()
            except OSError:
                pass
            try:
                announce.close()
            except OSError:
                pass
            return

        last_announce = 0.0
        try:
            while not self._stop.is_set():
                now = time.time()
                if now - last_announce >= 2.0:
                    ips = _local_ipv4s() or ["127.0.0.1"]
                    for ip in ips:
                        payload = self._payload(ip)
                        for target in self._announce_targets(ips):
                            try:
                                announce.sendto(payload, target)
                            except OSError:
                                pass
                    last_announce = now
                try:
                    data, addr = listen.recvfrom(2048)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not data:
                    continue
                # Ignore our own announces that somehow land here
                if data[:1] == b"{" and b'"service":"voxplayer"' in data:
                    continue
                if data.strip() == PROBE or data.startswith(b"VOXPLAYER_DISCOVER"):
                    for ip in _local_ipv4s() or ["127.0.0.1"]:
                        try:
                            announce.sendto(self._payload(ip), addr)
                        except OSError:
                            pass
        finally:
            try:
                listen.close()
            except OSError:
                pass
            try:
                announce.close()
            except OSError:
                pass

    def start(self) -> bool:
        if not discovery_enabled():
            return False
        if self._thread is not None:
            return True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="voxplayer-discovery", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        t = self._thread
        self._thread = None
        if t is not None:
            t.join(timeout=2.0)
