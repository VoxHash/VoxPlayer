"""Optional localhost HTTP control surface for trusted-LAN / script control.

Default bind: ``127.0.0.1:17890`` (override with ``VOXPLAYER_DAEMON_HOST`` /
``VOXPLAYER_DAEMON_PORT``). Disabled when ``VOXPLAYER_DAEMON=0``.

Endpoints (JSON)::

    GET  /status
    GET  /library  query: limit (default 200), offset (default 0)
    GET  /playlists
    GET  /podcasts
    POST /play  /pause  /playpause  /stop  /next  /previous
    POST /volume   body: {"percent": 0-200}
    POST /seek     body: {"ms": int} or {"relative_ms": int}
    POST /open     body: {"path": "/abs/or/file"}

Bluetooth RFCOMM control (optional, ``VOXPLAYER_BT=1``) shares the same command
surface as JSON lines — see ``voxplayer.bt_control``.

Browser / TUI remotes::

    GET  /ui   /ui/   /ui/app.js   — packaged web client (same-origin)
    CORS headers on all JSON responses for external pages / future WASM hosts
"""

from __future__ import annotations

import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

from .bt_control import BluetoothControlServer
from .discovery import DiscoveryBeacon


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 17890

_WEB_CLIENT_DIR = Path(__file__).resolve().parent / "web_client"
_CORS_HEADERS = (
    ("Access-Control-Allow-Origin", "*"),
    ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
    ("Access-Control-Allow-Headers", "Content-Type, Accept"),
    ("Access-Control-Max-Age", "86400"),
)


def daemon_enabled() -> bool:
    raw = os.environ.get("VOXPLAYER_DAEMON", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def daemon_bind() -> tuple:
    host = os.environ.get("VOXPLAYER_DAEMON_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    try:
        port = int(os.environ.get("VOXPLAYER_DAEMON_PORT", str(DEFAULT_PORT)))
    except ValueError:
        port = DEFAULT_PORT
    return host, port


class ControlDaemon:
    """Thin threaded HTTP server; callbacks run on the server thread — keep them safe."""

    def __init__(self, version: str = ""):
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, Callable[..., Any]] = {}
        self._beacon: Optional[DiscoveryBeacon] = None
        self._bt: Optional[BluetoothControlServer] = None
        self.host = DEFAULT_HOST
        self.port = DEFAULT_PORT
        self.version = version or ""

    def set_callbacks(self, **kwargs: Callable[..., Any]) -> None:
        self._callbacks.update(kwargs)

    def _dispatch_command(self, cmd: str, body: dict) -> dict:
        """Shared by HTTP POST and Bluetooth RFCOMM JSON lines."""
        key_map = {
            "status": "status",
            "library": "library",
            "playlists": "playlists",
            "podcasts": "podcasts",
            "play": "play",
            "pause": "pause",
            "playpause": "play_pause",
            "play_pause": "play_pause",
            "stop": "stop",
            "next": "next",
            "previous": "previous",
            "volume": "volume",
            "seek": "seek",
            "open": "open",
            "share": "share",
        }
        key = key_map.get((cmd or "").strip().lower())
        if not key:
            return {"ok": False, "error": "unknown_cmd", "cmd": cmd}
        fn = self._callbacks.get(key)
        if not callable(fn):
            return {"ok": False, "error": "not_implemented", "cmd": cmd}
        if key in {"status"}:
            data = fn()
            return data if isinstance(data, dict) else {"ok": True}
        if key in {"library", "playlists", "podcasts", "volume", "seek", "open"}:
            data = fn(body if isinstance(body, dict) else {})
            return data if isinstance(data, dict) else {"ok": True}
        data = fn()
        return data if isinstance(data, dict) else {"ok": True}

    def start(self) -> bool:
        if not daemon_enabled():
            return False
        if self._server is not None:
            return True
        self.host, self.port = daemon_bind()
        # Safety: refuse non-loopback unless explicitly opted in
        if self.host not in {"127.0.0.1", "localhost", "::1"} and not os.environ.get(
            "VOXPLAYER_DAEMON_ALLOW_LAN", ""
        ).strip().lower() in {"1", "true", "yes"}:
            self.host = "127.0.0.1"
        callbacks = self._callbacks
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def _cors(self) -> None:
                for k, v in _CORS_HEADERS:
                    self.send_header(k, v)

            def _json(self, code: int, payload: dict) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self._cors()
                self.end_headers()
                self.wfile.write(body)

            def _read_json(self) -> dict:
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0:
                    return {}
                raw = self.rfile.read(length)
                try:
                    data = json.loads(raw.decode("utf-8"))
                    return data if isinstance(data, dict) else {}
                except Exception:
                    return {}

            def _serve_ui(self, rel: str) -> bool:
                """Serve packaged web client under /ui. Returns True if handled."""
                raw_path = urlparse(self.path).path
                if raw_path in {"/ui", "/ui/"}:
                    rel = "index.html"
                elif raw_path.startswith("/ui/"):
                    rel = raw_path[len("/ui/") :]
                else:
                    return False
                # Path traversal guard
                if ".." in rel.split("/") or rel.startswith("/"):
                    self._json(404, {"error": "not_found"})
                    return True
                target = (_WEB_CLIENT_DIR / rel).resolve()
                try:
                    target.relative_to(_WEB_CLIENT_DIR.resolve())
                except ValueError:
                    self._json(404, {"error": "not_found"})
                    return True
                if not target.is_file():
                    self._json(404, {"error": "not_found"})
                    return True
                data = target.read_bytes()
                ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self._cors()
                self.end_headers()
                self.wfile.write(data)
                return True

            def do_OPTIONS(self):
                self.send_response(204)
                self._cors()
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_GET(self):
                if self._serve_ui(""):
                    return
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"
                if path == "/status":
                    fn = callbacks.get("status")
                    data = fn() if callable(fn) else {}
                    self._json(200, data if isinstance(data, dict) else {})
                    return
                if path == "/library":
                    from urllib.parse import parse_qs

                    qs = parse_qs(parsed.query or "")
                    try:
                        limit = int((qs.get("limit") or ["200"])[0])
                    except ValueError:
                        limit = 200
                    try:
                        offset = int((qs.get("offset") or ["0"])[0])
                    except ValueError:
                        offset = 0
                    try:
                        data = parent._dispatch_command(
                            "library", {"limit": limit, "offset": offset}
                        )
                    except Exception as exc:
                        self._json(500, {"error": str(exc)})
                        return
                    self._json(200, data if isinstance(data, dict) else {})
                    return
                if path == "/playlists":
                    try:
                        data = parent._dispatch_command("playlists", {})
                    except Exception as exc:
                        self._json(500, {"error": str(exc)})
                        return
                    self._json(200, data if isinstance(data, dict) else {})
                    return
                if path == "/podcasts":
                    try:
                        data = parent._dispatch_command("podcasts", {})
                    except Exception as exc:
                        self._json(500, {"error": str(exc)})
                        return
                    self._json(200, data if isinstance(data, dict) else {})
                    return
                if path in {"", "/"}:
                    self._json(
                        200,
                        {
                            "service": "voxplayer-control",
                            "host": parent.host,
                            "port": parent.port,
                            "endpoints": [
                                "/status",
                                "/library",
                                "/playlists",
                                "/podcasts",
                                "/play",
                                "/pause",
                                "/playpause",
                                "/stop",
                                "/next",
                                "/previous",
                                "/volume",
                                "/seek",
                                "/open",
                                "/ui",
                            ],
                            "bluetooth": {
                                "enabled": parent._bt is not None and parent._bt.active,
                                "channel": getattr(parent._bt, "channel", None),
                            },
                        },
                    )
                    return
                self._json(404, {"error": "not_found"})

            def do_POST(self):
                path = urlparse(self.path).path.rstrip("/") or "/"
                body = self._read_json()
                mapping = {
                    "/play": "play",
                    "/pause": "pause",
                    "/playpause": "playpause",
                    "/stop": "stop",
                    "/next": "next",
                    "/previous": "previous",
                    "/volume": "volume",
                    "/seek": "seek",
                    "/open": "open",
                    "/share": "share",
                }
                cmd = mapping.get(path)
                if not cmd:
                    self._json(404, {"error": "not_found"})
                    return
                try:
                    result = parent._dispatch_command(cmd, body)
                    self._json(200, result if isinstance(result, dict) else {"ok": True})
                except Exception as exc:
                    self._json(500, {"error": str(exc)})

        try:
            self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        except OSError:
            self._server = None
            return False
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        # LAN discovery for phone/Quest Connect (UDP); works even when HTTP is loopback-only
        # so USB reverse still functions, while Wi‑Fi peers find LAN IPs in the payload.
        try:
            self._beacon = DiscoveryBeacon(
                http_host=self.host,
                http_port=self.port,
                version=self.version,
            )
            self._beacon.start()
        except Exception:
            self._beacon = None
        try:
            self._bt = BluetoothControlServer(self._dispatch_command)
            self._bt.start()
        except Exception:
            self._bt = None
        return True

    def stop(self) -> None:
        if self._bt is not None:
            try:
                self._bt.stop()
            except Exception:
                pass
            self._bt = None
        if self._beacon is not None:
            try:
                self._beacon.stop()
            except Exception:
                pass
            self._beacon = None
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass
            self._server = None
        self._thread = None
