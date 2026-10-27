"""
Metadata + thumbnail worker pool for the desktop shell.

Prefers **linked FOSS libav (PyAV)** so tags/thumbs work without an ``ffmpeg`` /
``ffprobe`` binary on PATH. Falls back to the optional Rust ``vox_meta`` pool
(which still shells to the CLI when present).

Build Rust pool::

    cargo build --release --manifest-path native/Cargo.toml

Python queues jobs; results arrive via a thread-safe queue that the Qt shell
drains on the UI thread (never touch widgets from workers).
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
import threading
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

KIND_TAGS = 0
KIND_THUMB = 1
_NEXT_JOB_ID = 1
_JOB_LOCK = threading.Lock()

_Callback = ctypes.CFUNCTYPE(
    None,
    ctypes.c_void_p,
    ctypes.c_uint64,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int,
)

_LIB: Optional[ctypes.CDLL] = None
_LOAD_ERROR: Optional[str] = None


def _search_roots() -> List[str]:
    """Locate ``native/target`` from source tree, venv install, or env override."""
    here = os.path.dirname(os.path.abspath(__file__))
    roots: List[str] = []
    env = os.environ.get("VOXPLAYER_NATIVE_DIR", "").strip()
    if env:
        roots.extend([env, os.path.join(env, "target"), os.path.join(env, "release")])
    # Source checkout: voxplayer/../native/target
    roots.append(os.path.abspath(os.path.join(here, "..", "native", "target")))
    # pip install into project .venv: site-packages/voxplayer → repo root (5 up)
    roots.append(os.path.abspath(os.path.join(here, "..", "..", "..", "..", "..", "native", "target")))
    # Dedupe while preserving order
    seen = set()
    out: List[str] = []
    for r in roots:
        if r and r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _candidate_paths() -> List[str]:
    names = {
        "linux": ["libvox_meta.so"],
        "darwin": ["libvox_meta.dylib"],
        "win32": ["vox_meta.dll", "libvox_meta.dll"],
    }
    plat = (
        "win32"
        if sys.platform.startswith("win")
        else ("darwin" if sys.platform == "darwin" else "linux")
    )
    out: List[str] = []
    for root in _search_roots():
        for build in ("release", "debug", ""):
            base = os.path.join(root, build) if build else root
            for name in names[plat]:
                out.append(os.path.join(base, name))
    return out


def load_library() -> Optional[ctypes.CDLL]:
    global _LIB, _LOAD_ERROR
    if _LIB is not None:
        return _LIB
    for path in _candidate_paths():
        if not os.path.isfile(path):
            continue
        try:
            lib = ctypes.CDLL(path)
            lib.vox_meta_pool_create.argtypes = [ctypes.c_uint]
            lib.vox_meta_pool_create.restype = ctypes.c_void_p
            lib.vox_meta_pool_destroy.argtypes = [ctypes.c_void_p]
            lib.vox_meta_pool_destroy.restype = None
            lib.vox_meta_submit.argtypes = [
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_char_p,
                ctypes.c_double,
                _Callback,
                ctypes.c_void_p,
            ]
            lib.vox_meta_submit.restype = ctypes.c_uint64
            lib.vox_meta_version.argtypes = []
            lib.vox_meta_version.restype = ctypes.c_char_p
            _LIB = lib
            _LOAD_ERROR = None
            return _LIB
        except OSError as exc:
            _LOAD_ERROR = str(exc)
    _LOAD_ERROR = _LOAD_ERROR or "vox_meta shared library not found (build native/vox_meta)"
    return None


def is_available() -> bool:
    return load_library() is not None


def load_error() -> Optional[str]:
    load_library()
    return _LOAD_ERROR


def _alloc_job_id() -> int:
    global _NEXT_JOB_ID
    with _JOB_LOCK:
        jid = _NEXT_JOB_ID
        _NEXT_JOB_ID += 1
        return jid


class NativeMediaWorkers(QObject):
    """Queue tags/thumbnail jobs (FOSS libav preferred; Rust CLI fallback)."""

    tags_ready = pyqtSignal(str, dict)  # path, tag dict
    thumb_ready = pyqtSignal(str, str)  # path, jpeg path
    job_failed = pyqtSignal(str, int, str)  # path, kind, error

    def __init__(self, parent=None, workers: int = 0):
        super().__init__(parent)
        self._pool = None
        self._cb = None
        self._backend = ""  # "libav" | "rust"
        self._pending: Deque[Tuple] = deque()
        self._lock = threading.Lock()
        self._inflight_thumbs: Dict[str, bool] = {}
        self._inflight_tags: Dict[str, bool] = {}
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._drain)

        from voxplayer.media import libav_io

        libav_ok, _ = libav_io.available()
        if libav_ok:
            self._backend = "libav"
            self._timer.start()
            return

        lib = load_library()
        if lib is None:
            return
        self._pool = lib.vox_meta_pool_create(ctypes.c_uint(workers))
        if not self._pool:
            return
        # Keep callback alive for the lifetime of the pool.
        self._cb = _Callback(self._on_native_done)
        self._backend = "rust"
        self._timer.start()

    @property
    def available(self) -> bool:
        if self._backend == "libav":
            return True
        return self._pool is not None and self._cb is not None

    @property
    def backend(self) -> str:
        return self._backend

    def _on_native_done(self, _user, job_id, kind, path_b, result_b, status):
        path = (path_b or b"").decode("utf-8", errors="replace")
        result = (result_b or b"").decode("utf-8", errors="replace")
        with self._lock:
            self._pending.append((int(job_id), int(kind), path, result, int(status)))

    def _enqueue_done(self, job_id: int, kind: int, path: str, result: str, status: int) -> None:
        with self._lock:
            self._pending.append((int(job_id), int(kind), path, result, int(status)))

    def _drain(self) -> None:
        batch: List[Tuple] = []
        with self._lock:
            while self._pending and len(batch) < 32:
                batch.append(self._pending.popleft())
        for _jid, kind, path, result, status in batch:
            if kind == KIND_THUMB:
                self._inflight_thumbs.pop(path, None)
            elif kind == KIND_TAGS:
                self._inflight_tags.pop(path, None)
            if status != 0:
                self.job_failed.emit(path, kind, result or "native job failed")
                continue
            if kind == KIND_TAGS:
                try:
                    data = json.loads(result) if result else {}
                except json.JSONDecodeError:
                    data = {}
                if isinstance(data, dict):
                    self.tags_ready.emit(path, data)
            elif kind == KIND_THUMB:
                if result and os.path.isfile(result):
                    self.thumb_ready.emit(path, result)

    def submit_tags(self, path: str) -> int:
        if not self.available or not path or not os.path.isfile(path):
            return 0
        if self._inflight_tags.get(path):
            return 0
        if self._backend == "libav":
            return self._submit_tags_libav(path)
        lib = load_library()
        if lib is None:
            return 0
        self._inflight_tags[path] = True
        jid = lib.vox_meta_submit(
            self._pool,
            KIND_TAGS,
            path.encode("utf-8"),
            None,
            ctypes.c_double(0.0),
            self._cb,
            None,
        )
        if not jid:
            self._inflight_tags.pop(path, None)
        return int(jid or 0)

    def _submit_tags_libav(self, path: str) -> int:
        from voxplayer.media import libav_io

        jid = _alloc_job_id()
        self._inflight_tags[path] = True

        def _run() -> None:
            try:
                tags = libav_io.read_tags(path)
                # Shape matches Rust vox_meta JSON (title/artist/…)
                payload = {
                    "title": tags.get("title") or tags.get("track") or "",
                    "artist": tags.get("artist")
                    or tags.get("album_artist")
                    or tags.get("albumartist")
                    or "",
                    "album": tags.get("album") or "",
                    "year": (tags.get("date") or tags.get("year") or "")[:4],
                    "genre": tags.get("genre") or "",
                    "duration": float(tags.get("duration") or 0) or 0.0,
                }
                self._enqueue_done(jid, KIND_TAGS, path, json.dumps(payload), 0)
            except Exception as exc:
                self._enqueue_done(jid, KIND_TAGS, path, str(exc), 1)

        threading.Thread(target=_run, name="vox-meta-libav-tags", daemon=True).start()
        return jid

    def submit_thumb(self, path: str, cache_dir: str, seek: float = 3.0) -> int:
        if not self.available or not path or not os.path.isfile(path):
            return 0
        if self._inflight_thumbs.get(path):
            return 0
        if self._backend == "libav":
            return self._submit_thumb_libav(path, cache_dir, seek)
        lib = load_library()
        if lib is None:
            return 0
        os.makedirs(cache_dir, exist_ok=True)
        self._inflight_thumbs[path] = True
        jid = lib.vox_meta_submit(
            self._pool,
            KIND_THUMB,
            path.encode("utf-8"),
            cache_dir.encode("utf-8"),
            ctypes.c_double(float(seek)),
            self._cb,
            None,
        )
        if not jid:
            self._inflight_thumbs.pop(path, None)
        return int(jid or 0)

    def _submit_thumb_libav(self, path: str, cache_dir: str, seek: float) -> int:
        jid = _alloc_job_id()
        os.makedirs(cache_dir, exist_ok=True)
        self._inflight_thumbs[path] = True

        def _run() -> None:
            try:
                from voxplayer.media.thumbnails import ThumbnailCache

                # ThumbnailCache writes under its own cache root; ensure() is FOSS-first.
                out = ThumbnailCache().ensure(path, seek_seconds=float(seek))
                if out and os.path.isfile(out):
                    self._enqueue_done(jid, KIND_THUMB, path, out, 0)
                else:
                    self._enqueue_done(jid, KIND_THUMB, path, "libav thumb failed", 1)
            except Exception as exc:
                self._enqueue_done(jid, KIND_THUMB, path, str(exc), 1)

        threading.Thread(target=_run, name="vox-meta-libav-thumb", daemon=True).start()
        return jid

    def shutdown(self) -> None:
        self._timer.stop()
        lib = load_library()
        if lib is not None and self._pool:
            lib.vox_meta_pool_destroy(self._pool)
        self._pool = None
        self._cb = None
        self._backend = ""
