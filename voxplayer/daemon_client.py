"""HTTP client for the VoxPlayer localhost control daemon.

Shared by the TUI and scripted remotes. Default ``http://127.0.0.1:17890``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from urllib.parse import urljoin


def default_base_url() -> str:
    host = os.environ.get("VOXPLAYER_DAEMON_HOST", "127.0.0.1").strip() or "127.0.0.1"
    try:
        port = int(os.environ.get("VOXPLAYER_DAEMON_PORT", "17890"))
    except ValueError:
        port = 17890
    # Client always talks HTTP; host may be overridden for LAN peers.
    if "://" in host:
        return host.rstrip("/")
    return f"http://{host}:{port}"


class DaemonClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 2.0):
        self.base_url = (base_url or default_base_url()).rstrip("/") + "/"
        self.timeout = float(timeout)

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> Dict[str, Any]:
        url = urljoin(self.base_url, path.lstrip("/"))
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                if not raw:
                    return {"ok": True}
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {"ok": True, "data": parsed}
        except urllib.error.HTTPError as exc:
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
                payload = json.loads(err_body) if err_body else {}
            except Exception:
                payload = {}
            return {"ok": False, "error": payload.get("error") or f"HTTP {exc.code}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def root(self) -> Dict[str, Any]:
        return self._request("GET", "/")

    def status(self) -> Dict[str, Any]:
        return self._request("GET", "/status")

    def play(self) -> Dict[str, Any]:
        return self._request("POST", "/play", {})

    def pause(self) -> Dict[str, Any]:
        return self._request("POST", "/pause", {})

    def playpause(self) -> Dict[str, Any]:
        return self._request("POST", "/playpause", {})

    def stop(self) -> Dict[str, Any]:
        return self._request("POST", "/stop", {})

    def next(self) -> Dict[str, Any]:
        return self._request("POST", "/next", {})

    def previous(self) -> Dict[str, Any]:
        return self._request("POST", "/previous", {})

    def volume(self, percent: int) -> Dict[str, Any]:
        return self._request("POST", "/volume", {"percent": int(percent)})

    def seek(self, *, ms: Optional[int] = None, relative_ms: Optional[int] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if ms is not None:
            body["ms"] = int(ms)
        if relative_ms is not None:
            body["relative_ms"] = int(relative_ms)
        return self._request("POST", "/seek", body)

    def open_path(self, path: str) -> Dict[str, Any]:
        return self._request("POST", "/open", {"path": path})
