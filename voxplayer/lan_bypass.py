"""Keep RFC1918 / LAN traffic off the VPN path so companions can reach the desktop daemon.

ProtonVPN (and similar WireGuard clients) often install policy routing that sends
*all* destinations — including other home subnets — into the tunnel. The Android /
Quest companion then cannot open ``http://<desktop-lan-ip>:17890``.

This module:

* Detects VPN interfaces (``proton0``, ``wg*``, ``tun*``, ``tailscale0``, …)
* Detects physical LAN interfaces and their gateway
* Installs host routes for private ranges (and optional extra prefixes) via the
  LAN gateway so they stay local
* Prints a status report for e2e / operators

Requires root for ``ip route`` changes (``sudo`` / ``pkexec``). Safe to re-run.
Disable with ``voxplayer-lan-bypass off``.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Set, Tuple


VPN_IFACE_RE = re.compile(
    r"^(proton\d*|wg\d*|tun\d*|tailscale\d*|nordlynx|zt\w+|pvpnksintrf\d*)$",
    re.I,
)
PHYS_HINTS = ("en", "eth", "wl", "wlan", "usb", "rndis", "mac")

# Private + link-local-ish ranges companions commonly use. VPN tunnel addresses
# inside 10.0.0.0/8 that belong to the VPN iface are left alone by preferring
# more-specific connected routes already present.
DEFAULT_PREFIXES = (
    "192.168.0.0/16",
    "10.0.0.0/8",
    "172.16.0.0/12",
)

MARKER = "voxplayer-lan-bypass"


@dataclass
class LanPlan:
    lan_iface: str
    gateway: str
    prefixes: List[str] = field(default_factory=list)
    vpn_ifaces: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def _run(cmd: Sequence[str], *, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(cmd),
        check=check,
        text=True,
        capture_output=True,
    )


def _need_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() != 0


def _elevate(argv: List[str]) -> int:
    """Re-exec under sudo or pkexec when route changes need privileges."""
    if not _need_root():
        return -1
    sudo = shutil.which("sudo")
    if sudo:
        # Prefer non-interactive when already permitted; else prompt.
        trial = _run([sudo, "-n", "true"])
        cmd = [sudo, "-n", sys.executable, "-m", "voxplayer.lan_bypass", *argv] if trial.returncode == 0 else [
            sudo,
            sys.executable,
            "-m",
            "voxplayer.lan_bypass",
            *argv,
        ]
        return subprocess.call(cmd)
    pkexec = shutil.which("pkexec")
    if pkexec:
        return subprocess.call([pkexec, sys.executable, "-m", "voxplayer.lan_bypass", *argv])
    print(
        "Root required to install LAN routes. Install sudo/pkexec or run as root:\n"
        f"  {sys.executable} -m voxplayer.lan_bypass {' '.join(argv)}",
        file=sys.stderr,
    )
    return 1


def list_ifaces() -> List[Tuple[str, str]]:
    """Return (iface, ipv4_cidr) for UP interfaces."""
    out = _run(["ip", "-4", "-o", "addr", "show", "up"])
    rows: List[Tuple[str, str]] = []
    for line in (out.stdout or "").splitlines():
        # 2: enp8s0    inet 192.168.1.238/24 ...
        parts = line.split()
        if len(parts) < 4:
            continue
        iface = parts[1]
        if "inet" not in parts:
            continue
        cidr = parts[parts.index("inet") + 1]
        rows.append((iface, cidr))
    return rows


def detect_vpn_ifaces(ifaces: Iterable[str]) -> List[str]:
    found: List[str] = []
    for name in ifaces:
        base = name.split("@", 1)[0]
        if VPN_IFACE_RE.match(base) or base.startswith("proton") or base.startswith("pvpn"):
            found.append(base)
    return sorted(set(found))


def pick_lan_iface(pairs: Sequence[Tuple[str, str]], vpn: Set[str]) -> Optional[Tuple[str, str]]:
    candidates: List[Tuple[str, str]] = []
    for iface, cidr in pairs:
        base = iface.split("@", 1)[0]
        if base in vpn or base == "lo":
            continue
        if base.startswith("br-") or base.startswith("docker") or base.startswith("veth"):
            continue
        if any(base.startswith(h) for h in PHYS_HINTS):
            candidates.append((base, cidr))
    if not candidates:
        return None
    # Prefer ethernet over wifi when both present.
    candidates.sort(key=lambda ic: (0 if ic[0].startswith(("en", "eth")) else 1, ic[0]))
    return candidates[0]


def default_gateway(iface: str) -> Optional[str]:
    out = _run(["ip", "-4", "route", "show", "default"])
    for line in (out.stdout or "").splitlines():
        if f"dev {iface}" not in line:
            continue
        m = re.search(r"via\s+(\S+)", line)
        if m:
            return m.group(1)
    # Fallback: any default via that iface in the main table
    out = _run(["ip", "-4", "route", "show", "table", "main"])
    for line in (out.stdout or "").splitlines():
        if line.startswith("default") and f"dev {iface}" in line:
            m = re.search(r"via\s+(\S+)", line)
            if m:
                return m.group(1)
    return None


def build_plan(extra_prefixes: Optional[Sequence[str]] = None) -> LanPlan:
    pairs = list_ifaces()
    vpn = detect_vpn_ifaces(i for i, _ in pairs)
    # Also scan link names that may lack an IPv4 (pvpnksintrf)
    link = _run(["ip", "-o", "link", "show"])
    for line in (link.stdout or "").splitlines():
        m = re.match(r"\d+:\s+([^:@]+)", line)
        if m:
            name = m.group(1)
            if VPN_IFACE_RE.match(name) and name not in vpn:
                vpn.append(name)
    lan = pick_lan_iface(pairs, set(vpn))
    notes: List[str] = []
    if not lan:
        notes.append("No physical LAN interface with IPv4 found.")
        return LanPlan(lan_iface="", gateway="", prefixes=[], vpn_ifaces=vpn, notes=notes)
    iface, cidr = lan
    gw = default_gateway(iface)
    if not gw:
        # Use the interface as an on-link path for its own subnet only.
        notes.append(f"No default gateway on {iface}; will install on-link routes where possible.")
        gw = ""
    prefixes = list(DEFAULT_PREFIXES)
    if extra_prefixes:
        prefixes.extend(extra_prefixes)
    # Always include the local subnet explicitly.
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        prefixes.insert(0, str(net))
    except ValueError:
        pass
    # Dedupe while preserving order
    seen: Set[str] = set()
    ordered: List[str] = []
    for p in prefixes:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    if vpn:
        notes.append("VPN ifaces detected: " + ", ".join(vpn))
    else:
        notes.append("No VPN iface matched; routes still help multi-subnet homes.")
    return LanPlan(lan_iface=iface, gateway=gw, prefixes=ordered, vpn_ifaces=vpn, notes=notes)


def _route_exists(prefix: str, iface: str) -> bool:
    out = _run(["ip", "-4", "route", "show", prefix])
    text = out.stdout or ""
    return iface in text or "via" in text


def apply_plan(plan: LanPlan, *, dry_run: bool = False) -> List[str]:
    actions: List[str] = []
    if not plan.lan_iface:
        actions.append("skip: no LAN iface")
        return actions
    for prefix in plan.prefixes:
        if plan.gateway:
            cmd = [
                "ip",
                "route",
                "replace",
                prefix,
                "via",
                plan.gateway,
                "dev",
                plan.lan_iface,
                "protocol",
                "static",
            ]
        else:
            cmd = [
                "ip",
                "route",
                "replace",
                prefix,
                "dev",
                plan.lan_iface,
                "protocol",
                "static",
                "scope",
                "link",
            ]
        actions.append(" ".join(cmd))
        if dry_run:
            continue
        cp = _run(cmd)
        if cp.returncode != 0:
            actions.append(f"  ! failed: {(cp.stderr or cp.stdout or '').strip()}")
    # Marker file for status/off
    marker_path = os.path.expanduser("~/.cache/voxplayer/lan_bypass.json")
    if not dry_run:
        os.makedirs(os.path.dirname(marker_path), exist_ok=True)
        with open(marker_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "marker": MARKER,
                    "lan_iface": plan.lan_iface,
                    "gateway": plan.gateway,
                    "prefixes": plan.prefixes,
                    "vpn_ifaces": plan.vpn_ifaces,
                },
                fh,
                indent=2,
            )
            fh.write("\n")
    return actions


def remove_plan(*, dry_run: bool = False) -> List[str]:
    marker_path = os.path.expanduser("~/.cache/voxplayer/lan_bypass.json")
    actions: List[str] = []
    prefixes: List[str] = list(DEFAULT_PREFIXES)
    if os.path.isfile(marker_path):
        try:
            with open(marker_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            prefixes = list(data.get("prefixes") or prefixes)
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    for prefix in prefixes:
        cmd = ["ip", "route", "del", prefix]
        actions.append(" ".join(cmd))
        if dry_run:
            continue
        _run(cmd)  # ignore errors if already gone
    if not dry_run and os.path.isfile(marker_path):
        try:
            os.unlink(marker_path)
        except OSError:
            pass
    return actions


def status_report() -> dict:
    plan = build_plan()
    route_get = {}
    for sample in ("192.168.1.1", "192.168.68.1", "10.0.0.1"):
        cp = _run(["ip", "route", "get", sample])
        route_get[sample] = (cp.stdout or cp.stderr or "").strip()
    return {
        "plan": {
            "lan_iface": plan.lan_iface,
            "gateway": plan.gateway,
            "prefixes": plan.prefixes,
            "vpn_ifaces": plan.vpn_ifaces,
            "notes": plan.notes,
        },
        "route_get": route_get,
        "daemon_hint": {
            "VOXPLAYER_DAEMON_ALLOW_LAN": "1",
            "VOXPLAYER_DAEMON_HOST": "0.0.0.0",
            "port": 17890,
        },
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="voxplayer-lan-bypass",
        description="Route LAN/RFC1918 traffic outside the VPN so phone/Quest companions work.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="status",
        choices=("status", "on", "off", "apply", "plan"),
        help="status (default), on/apply, off, or plan (dry-run)",
    )
    parser.add_argument(
        "--prefix",
        action="append",
        default=[],
        help="Extra CIDR to keep on LAN (repeatable), e.g. --prefix 192.168.68.0/24",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command in {"on", "apply", "off"} and _need_root():
        # Re-exec elevated with the same args (without duplicating elevate loops).
        rc = _elevate(sys.argv[1:])
        return rc if rc >= 0 else 1

    if args.command == "status":
        report = status_report()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            p = report["plan"]
            print(f"LAN iface : {p['lan_iface'] or '(none)'}")
            print(f"Gateway   : {p['gateway'] or '(none)'}")
            print(f"VPN ifaces: {', '.join(p['vpn_ifaces']) or '(none)'}")
            print(f"Prefixes  : {', '.join(p['prefixes'])}")
            for n in p["notes"]:
                print(f"Note      : {n}")
            print("Route samples:")
            for host, line in report["route_get"].items():
                print(f"  {host} -> {line}")
            print(
                "Daemon   : export VOXPLAYER_DAEMON_ALLOW_LAN=1 "
                "VOXPLAYER_DAEMON_HOST=0.0.0.0"
            )
        return 0

    if args.command == "plan":
        plan = build_plan(extra_prefixes=args.prefix)
        actions = apply_plan(plan, dry_run=True)
        if args.json:
            print(json.dumps({"plan": plan.__dict__, "actions": actions}, indent=2))
        else:
            for a in actions:
                print(a)
        return 0

    if args.command in {"on", "apply"}:
        plan = build_plan(extra_prefixes=args.prefix)
        if not plan.lan_iface:
            print("No LAN interface to bind routes to.", file=sys.stderr)
            return 2
        actions = apply_plan(plan, dry_run=False)
        for a in actions:
            print(a)
        print("LAN bypass applied. Re-test companion → desktop IP:17890.")
        return 0

    if args.command == "off":
        actions = remove_plan(dry_run=False)
        for a in actions:
            print(a)
        print("LAN bypass routes removed (best-effort).")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
