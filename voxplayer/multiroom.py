"""LAN multi-room sync via peer VoxPlayer control daemons.

No Chromecast / AirPlay / second media stack — each room runs the same native
C core. The leader fans out play/pause/seek/volume/open to configured peers
(``VOXPLAYER_DAEMON_ALLOW_LAN=1`` required on room hosts).
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _config_path() -> str:
    root = os.path.join(os.path.expanduser("~"), ".config", "voxplayer")
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "multiroom.json")


@dataclass
class RoomPeer:
    name: str
    host: str
    port: int = 17890
    enabled: bool = True

    def base_url(self) -> str:
        host = (self.host or "").strip() or "127.0.0.1"
        port = int(self.port) if self.port else 17890
        return f"http://{host}:{port}"


@dataclass
class MultiroomConfig:
    sync_enabled: bool = False
    peers: List[RoomPeer] = field(default_factory=list)


def load_config() -> MultiroomConfig:
    path = _config_path()
    if not os.path.isfile(path):
        return MultiroomConfig()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError, TypeError):
        return MultiroomConfig()
    peers: List[RoomPeer] = []
    for item in data.get("peers") or []:
        if not isinstance(item, dict) or not item.get("host"):
            continue
        try:
            port = int(item.get("port") or 17890)
        except (TypeError, ValueError):
            port = 17890
        peers.append(
            RoomPeer(
                name=str(item.get("name") or item["host"]),
                host=str(item["host"]).strip(),
                port=port,
                enabled=bool(item.get("enabled", True)),
            )
        )
    return MultiroomConfig(
        sync_enabled=bool(data.get("sync_enabled", False)),
        peers=peers,
    )


def save_config(cfg: MultiroomConfig) -> None:
    payload = {
        "sync_enabled": bool(cfg.sync_enabled),
        "peers": [asdict(p) for p in cfg.peers],
    }
    path = _config_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def probe_peer(peer: RoomPeer, timeout: float = 1.5) -> Tuple[bool, str]:
    """GET /status on a peer; returns (ok, message)."""
    url = peer.base_url().rstrip("/") + "/status"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
            ver = data.get("version", "?")
            playing = data.get("playing")
            return True, f"ok (v{ver}, playing={playing})"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, str(exc)[:120]


def _post_json(url: str, body: Optional[dict], timeout: float) -> Tuple[bool, str]:
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "X-VoxPlayer-Multiroom": "1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, str(exc)[:120]


def fanout_action(
    peers: List[RoomPeer],
    action: str,
    body: Optional[Dict[str, Any]] = None,
    *,
    timeout: float = 1.2,
    async_: bool = True,
) -> None:
    """
    POST ``/{action}`` to every enabled peer.

    When ``async_`` is True, work runs on a daemon thread so the UI stays responsive.
    """
    action = (action or "").strip().lstrip("/")
    if not action:
        return
    targets = [p for p in peers if p.enabled and (p.host or "").strip()]
    if not targets:
        return

    def _run() -> None:
        for peer in targets:
            url = peer.base_url().rstrip("/") + "/" + action
            _post_json(url, body, timeout)

    if async_:
        threading.Thread(target=_run, name="vox-multiroom", daemon=True).start()
    else:
        _run()
