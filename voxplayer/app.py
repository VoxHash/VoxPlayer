#!/usr/bin/env python3
"""
VoxPlayer - A modern multimedia player built with PyQt6
Clean implementation without signal issues
"""

import sys
import os
import random
import tempfile
import shutil
import requests
import webbrowser
import json
import re
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple, Set
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QSlider, QLabel,
                            QFileDialog, QDockWidget, QListWidget, QListWidgetItem,
                            QMenuBar, QMenu, QStatusBar, QMessageBox, QInputDialog,
                            QLineEdit, QStackedWidget, QSizePolicy, QSystemTrayIcon,
                            QStyle, QDialog)
from PyQt6.QtCore import Qt, QTimer, QSettings, QUrl, QThread, pyqtSignal, QFileSystemWatcher
from PyQt6.QtGui import QKeySequence, QShortcut, QAction, QActionGroup, QIcon, QPixmap

from .theme import (
    COLORS,
    app_stylesheet,
    apply_theme_id,
    list_themes,
    user_themes_dir,
)
from .ui.shell import LeftRail, HomeView, NowPlayingPanel, TransportBar, AboutDialog
from .engine.playback import (
    PlaybackEngine,
    prefer_xcb_for_mpv_embed,
    NativeEngineError,
    show_native_engine_failure,
    embed_platform_hint,
    embed_status_message,
)
from .media.thumbnails import ThumbnailCache, get_thumbnail_path, _cache_root as _thumb_cache_root
from .media.metadata import (
    MediaMetadata,
    enrich_metadata,
    is_online,
    load_local_metadata,
)
from .media.torrent_gate import validate_torrent_file, validate_torrent_file_list
from .media.playlists import PlaylistStore
from .media.library_facets import group_library, VIDEO_EXT as FACET_VIDEO_EXT, AUDIO_EXT as FACET_AUDIO_EXT
from .native_scan import scan_media_dir, backend_name as scan_backend_name
from .native_workers import NativeMediaWorkers
from .library_index import LibraryIndex, DEFAULT_EXTS
from .ui.torrent_picker import TorrentFilePickerDialog, media_paths_only
from .mpris import MprisController
from .control_daemon import ControlDaemon
from .podcasts import PodcastStore, download_episode, podcasts_dir
from .subtitles import companion_subtitle_paths


class MetadataEnrichWorker(QThread):
    """Background offline-first enrichment (network only when online / refresh)."""

    finished_meta = pyqtSignal(object)

    def __init__(
        self,
        path: str,
        cover_path: str,
        parent=None,
        force_refresh: bool = False,
        allow_network: bool = True,
    ):
        super().__init__(parent)
        self.path = path
        self.cover_path = cover_path
        self.force_refresh = force_refresh
        self.allow_network = allow_network

    def run(self):
        try:
            meta = enrich_metadata(
                self.path,
                cover_dest=self.cover_path,
                force_refresh=self.force_refresh,
                allow_network=self.allow_network,
            )
        except Exception:
            try:
                meta = load_local_metadata(self.path)
            except Exception:
                meta = MediaMetadata(path=self.path)
        self.finished_meta.emit(meta)


# Data classes for state management
@dataclass
class AppState:
    window_geometry: Optional[bytes] = None
    theme: str = "ember"
    volume: int = 100
    last_file: str = ""
    resume_positions: Dict[str, int] = None
    auto_update_enabled: bool = True
    update_channel: str = "stable"
    audio_output_mode: str = "default"  # "default" or "manual"
    selected_audio_device: str = ""  # Device ID for manual mode
    library_roots: List[str] = None  # persisted Open Folder roots
    shuffle_enabled: bool = False
    repeat_mode: str = "off"  # off | one | all

    def __post_init__(self):
        if self.resume_positions is None:
            self.resume_positions = {}
        if self.library_roots is None:
            self.library_roots = []
        if self.repeat_mode not in ("off", "one", "all"):
            self.repeat_mode = "off"

def qbittorrent_webui_setup_text() -> str:
    """First-run / error copy for enabling the Web UI — never embeds secrets."""
    host = os.getenv("QB_HOST", "localhost:8080")
    return (
        "qBittorrent Web UI setup (required for torrent streaming)\n"
        "────────────────────────────────────────\n"
        "1. Open qBittorrent → Tools → Options → Web UI.\n"
        "2. Enable “Web User Interface (Remote control)”.\n"
        "3. Prefer “Bypass authentication for clients on localhost” for local use,\n"
        "   or set a username/password you choose yourself.\n"
        "4. Note the IP and port (default often 127.0.0.1:8080).\n"
        "5. Tell VoxPlayer via environment variables (optional if localhost + bypass):\n"
        f"     QB_HOST={host}\n"
        "     QB_USERNAME=…   (only if auth is required)\n"
        "     QB_PASSWORD=…   (only if auth is required; never commit these)\n"
        "\n"
        "VoxPlayer does not ship or store default passwords. Keep credentials in your\n"
        "shell profile or a private env file — not in the repository."
    )


@dataclass
class SubtitleTrack:
    index: int
    language: str
    name: str
    enabled: bool = True

@dataclass
class SubtitleStyle:
    font_family: str = "Arial"
    font_size: int = 16
    text_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    background_color: str = "transparent"
    bold: bool = False
    italic: bool = False

# Torrent streaming classes
class TorrentStreamer(QThread):
    """Thread for handling torrent streaming using qBittorrent API"""
    progress_updated = pyqtSignal(int, str)  # progress, status
    file_ready = pyqtSignal(str)  # file_path
    error_occurred = pyqtSignal(str)  # error_message

    def __init__(
        self,
        magnet_link: str = None,
        torrent_file: str = None,
        preferred_relative_path: str = None,
        preferred_relative_paths: List[str] = None,
    ):
        super().__init__()
        self.magnet_link = magnet_link
        self.torrent_file = torrent_file
        prefs = list(preferred_relative_paths or [])
        if preferred_relative_path:
            prefs.insert(0, preferred_relative_path)
        # Dedupe, normalize
        seen = set()
        normalized = []
        for p in prefs:
            n = (p or "").replace("\\", "/").lstrip("./")
            if n and n.lower() not in seen:
                seen.add(n.lower())
                normalized.append(n)
        self.preferred_relative_paths = normalized
        self.preferred_relative_path = normalized[0] if normalized else ""
        self.temp_dir = None
        self.is_running = False
        self.qb_client = None
        self.torrent_hash = None
        self.stream_file_path = None
        self.stream_file_index = None
        self.stream_file_size = 0
        self._file_ready_emitted = False
        self.stream_category = f"voxplayer_stream_{uuid.uuid4().hex[:10]}"

    def run(self):
        """Start torrent streaming"""
        try:
            self.is_running = True
            self.progress_updated.emit(0, "Initializing torrent client...")

            # Create temporary directory for torrent files
            self.temp_dir = tempfile.mkdtemp(prefix="voxplayer_torrent_")

            # Initialize qBittorrent client
            self._init_qbittorrent()

            # Add torrent
            if self.magnet_link:
                self._add_magnet_link()
            elif self.torrent_file:
                self._add_torrent_file()
            else:
                self.error_occurred.emit("No magnet link or torrent file provided")
                return

        except Exception as e:
            self.error_occurred.emit(f"Torrent streaming error: {str(e)}")
        finally:
            self.is_running = False

    def _init_qbittorrent(self):
        """Initialize qBittorrent client"""
        try:
            from qbittorrentapi import Client
            qb_host = os.getenv("QB_HOST", "localhost:8080")
            qb_username = os.getenv("QB_USERNAME", "")
            qb_password = os.getenv("QB_PASSWORD", "")

            host_only = qb_host.split(":")[0].strip().lower().strip("[]")
            is_loopback = host_only in {"localhost", "127.0.0.1", "::1"}

            def _connect(**client_kwargs):
                client = Client(**client_kwargs)
                app_version_attr = client.app.version
                version = app_version_attr() if callable(app_version_attr) else app_version_attr
                if not version:
                    raise RuntimeError("qBittorrent is not running. Please start qBittorrent first.")
                return client, str(version).lstrip("vV")

            # Prefer unauthenticated access on loopback when Web UI localhost bypass is enabled.
            # Sending a wrong password still counts as a failed login and can ban 127.0.0.1.
            if is_loopback:
                try:
                    self.qb_client, version = _connect(host=qb_host)
                    self.progress_updated.emit(10, f"Connected to qBittorrent v{version}")
                    return
                except Exception:
                    if not (qb_username and qb_password):
                        raise

            client_kwargs = {"host": qb_host}
            if qb_username and qb_password:
                client_kwargs["username"] = qb_username
                client_kwargs["password"] = qb_password

            self.qb_client, version = _connect(**client_kwargs)
            self.progress_updated.emit(10, f"Connected to qBittorrent v{version}")

        except ImportError as exc:
            raise RuntimeError(
                "qBittorrent API not available. Please install: pip install qbittorrent-api"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Failed to connect to qBittorrent at '{os.getenv('QB_HOST', 'localhost:8080')}'.\n\n"
                + qbittorrent_webui_setup_text()
            ) from exc

    def _add_magnet_link(self):
        """Add magnet link to qBittorrent"""
        try:
            if not self.qb_client:
                raise RuntimeError("qBittorrent client is not initialized.")
            self.progress_updated.emit(20, "Adding magnet link...")

            add_kwargs = {
                "urls": self.magnet_link,
                "save_path": self.temp_dir,
                "category": self.stream_category,
                "is_paused": False,
                "use_auto_torrent_management": False,
                "is_sequential_download": True,
                "is_first_last_piece_prio": True,
            }
            try:
                torrent_info = self.qb_client.torrents_add(**add_kwargs)
            except TypeError:
                # Older qBittorrent Web API versions do not support these add-time flags.
                add_kwargs.pop("is_sequential_download", None)
                add_kwargs.pop("is_first_last_piece_prio", None)
                torrent_info = self.qb_client.torrents_add(**add_kwargs)

            if self._torrent_add_succeeded(torrent_info):
                self.progress_updated.emit(30, "Magnet link added successfully")
                self._monitor_torrent()
            else:
                self.error_occurred.emit(f"Failed to add magnet link: {torrent_info}")

        except Exception as e:
            self.error_occurred.emit(f"Error adding magnet link: {str(e)}")

    def _torrent_info_hash(self) -> Optional[str]:
        """SHA-1 info hash from the local .torrent file (hex)."""
        if not self.torrent_file:
            return None
        try:
            from .media.bencode import decode as bdecode, encode as bencode
            import hashlib

            with open(self.torrent_file, "rb") as fh:
                meta = bdecode(fh.read())
            info = meta.get(b"info") if isinstance(meta, dict) else None
            if not isinstance(info, dict):
                return None
            return hashlib.sha1(bencode(info)).hexdigest()
        except Exception:
            return None

    def _reuse_existing_torrent(self) -> bool:
        """If qBittorrent already has this torrent, attach and continue streaming."""
        info_hash = self._torrent_info_hash()
        if not info_hash or not self.qb_client:
            return False
        try:
            items = self.qb_client.torrents_info(torrent_hashes=info_hash)
        except Exception:
            items = []
        if not items:
            # Fallback: match by torrent name
            try:
                from .media.bencode import decode as bdecode

                with open(self.torrent_file, "rb") as fh:
                    meta = bdecode(fh.read())
                name = meta.get(b"info", {}).get(b"name", b"")
                if isinstance(name, bytes):
                    name = name.decode("utf-8", errors="replace")
                for t in self.qb_client.torrents_info():
                    if str(getattr(t, "name", "")) == name:
                        items = [t]
                        break
            except Exception:
                items = []
        if not items:
            return False
        self.torrent_hash = str(getattr(items[0], "hash", info_hash) or info_hash)
        try:
            self.qb_client.torrents_set_category(
                torrent_hashes=self.torrent_hash, category=self.stream_category
            )
        except Exception:
            pass
        self.resume_transfer()
        self.progress_updated.emit(30, "Reusing existing torrent in qBittorrent")
        self._monitor_torrent()
        return True

    def _add_torrent_file(self):
        """Add torrent file to qBittorrent"""
        try:
            if not self.qb_client:
                raise RuntimeError("qBittorrent client is not initialized.")
            self.progress_updated.emit(20, "Adding torrent file...")

            # Read torrent file
            with open(self.torrent_file, 'rb') as f:
                torrent_data = f.read()

            add_kwargs = {
                "torrent_files": torrent_data,
                "save_path": self.temp_dir,
                "category": self.stream_category,
                "is_paused": False,
                "use_auto_torrent_management": False,
                "is_sequential_download": True,
                "is_first_last_piece_prio": True,
            }
            try:
                try:
                    torrent_info = self.qb_client.torrents_add(**add_kwargs)
                except TypeError:
                    add_kwargs.pop("is_sequential_download", None)
                    add_kwargs.pop("is_first_last_piece_prio", None)
                    torrent_info = self.qb_client.torrents_add(**add_kwargs)
            except Exception as add_exc:
                # qBittorrent returns HTTP 409 Conflict when the torrent already exists.
                msg = str(add_exc).lower()
                if "conflict" in msg or "already" in msg:
                    if self._reuse_existing_torrent():
                        return
                raise

            if self._torrent_add_succeeded(torrent_info):
                self.progress_updated.emit(30, "Torrent file added successfully")
                self._monitor_torrent()
            else:
                # Some builds return Fails when already present — reuse by hash.
                info_s = str(torrent_info).lower()
                if "fail" in info_s or "exist" in info_s or torrent_info == "Fails.":
                    if self._reuse_existing_torrent():
                        return
                self.error_occurred.emit(f"Failed to add torrent file: {torrent_info}")

        except Exception as e:
            msg = str(e).lower()
            if "conflict" in msg or "already" in msg:
                if self._reuse_existing_torrent():
                    return
            self.error_occurred.emit(f"Error adding torrent file: {str(e)}")

    def _torrent_add_succeeded(self, torrent_info) -> bool:
        """True when torrents_add reports success across qbittorrent-api versions."""
        if isinstance(torrent_info, str):
            return torrent_info.lower().startswith("ok")
        success_count = getattr(torrent_info, "success_count", None)
        if success_count is not None:
            return int(success_count) > 0
        added_ids = getattr(torrent_info, "added_torrent_ids", None)
        if added_ids is not None:
            return len(added_ids) > 0
        # Legacy clients may return None on success.
        return torrent_info is None

    def _monitor_torrent(self):
        """Monitor torrent progress and emit media file once buffer is ready."""
        try:
            if not self.torrent_hash:
                self.torrent_hash = self._wait_for_torrent_hash()
            if not self.torrent_hash:
                self.error_occurred.emit("Unable to locate added torrent in qBittorrent.")
                return

            self._configure_streaming_mode()

            while self.is_running:
                torrent_items = self.qb_client.torrents_info(torrent_hashes=self.torrent_hash)
                if not torrent_items:
                    self.error_occurred.emit("Torrent disappeared from qBittorrent.")
                    break
                torrent_info = torrent_items[0]

                progress = int(float(getattr(torrent_info, "progress", 0.0)) * 100)
                state = str(getattr(torrent_info, "state", "unknown"))
                dlspeed = int(getattr(torrent_info, "dlspeed", 0) or 0)
                speed_mbps = dlspeed / (1024 * 1024)
                self.progress_updated.emit(
                    40 + progress // 2,
                    f"{state} | {progress}% | {speed_mbps:.2f} MiB/s",
                )

                if not self._file_ready_emitted:
                    ready, downloaded, required = self._is_buffer_ready()
                    if ready and self.stream_file_path:
                        self._file_ready_emitted = True
                        self.progress_updated.emit(
                            90,
                            f"Buffer ready ({downloaded // (1024 * 1024)} / {required // (1024 * 1024)} MiB), starting playback",
                        )
                        self.file_ready.emit(self.stream_file_path)
                    elif required > 0:
                        self.progress_updated.emit(
                            55,
                            f"Buffering {downloaded // (1024 * 1024)} / {required // (1024 * 1024)} MiB",
                        )
                        if dlspeed <= 128 * 1024:
                            self.progress_updated.emit(
                                56,
                                "Low download speed detected, playback may stutter",
                            )

                if state in {"error", "missingFiles"}:
                    self.error_occurred.emit(f"Torrent error: {state}")
                    break

                time.sleep(1.5)

        except Exception as e:
            self.error_occurred.emit(f"Error monitoring torrent: {str(e)}")

    def _wait_for_torrent_hash(self, timeout_seconds: int = 60) -> Optional[str]:
        """Wait until qBittorrent registers the newly added torrent."""
        deadline = time.time() + timeout_seconds
        while self.is_running and time.time() < deadline:
            try:
                torrents = self.qb_client.torrents_info(category=self.stream_category)
            except Exception:
                torrents = []

            if torrents:
                torrents = sorted(
                    torrents,
                    key=lambda t: int(getattr(t, "added_on", 0) or 0),
                    reverse=True,
                )
                selected = torrents[0]
                self.progress_updated.emit(35, f"Metadata acquired: {selected.name}")
                return selected.hash

            self.progress_updated.emit(34, "Waiting for metadata and peers...")
            time.sleep(1.0)
        return None

    def _configure_streaming_mode(self):
        """Enable sequential streaming mode and pick one playable media file."""
        self._set_sequential_download()
        self._set_first_last_piece_priority()

        # Post-metadata gate (magnets / client file list)
        file_names = []
        for item in self._torrent_files():
            name = str(getattr(item, "name", "") or "")
            if name:
                file_names.append(name)
        ok, gate_msg = validate_torrent_file_list(file_names)
        if not ok:
            raise RuntimeError(gate_msg)

        stream_file = self._pick_stream_file()
        if not stream_file:
            raise RuntimeError("No supported media file found in torrent contents.")

        file_name = str(getattr(stream_file, "name", ""))
        file_index = self._file_index(stream_file)
        file_size = int(getattr(stream_file, "size", 0) or 0)
        if file_index is None:
            raise RuntimeError("Unable to identify media file index for streaming priority.")

        self.stream_file_index = file_index
        self.stream_file_size = file_size
        self.stream_file_path = os.path.join(self.temp_dir, file_name)

        self._seq_reasserted = False
        self._prioritize_selected_file(file_index)
        buf_mb = max(1, self._buffer_target_bytes() // (1024 * 1024))
        self.progress_updated.emit(
            45,
            f"Sequential mode + ~{buf_mb} MiB buffer for {os.path.basename(file_name)}",
        )

    def _set_sequential_download(self):
        """Attempt to force sequential piece ordering."""
        try:
            self.qb_client.torrents_set_sequential_download(
                torrent_hashes=self.torrent_hash, value=True
            )
            return
        except Exception:
            pass
        try:
            self.qb_client.torrents_toggle_sequential_download(
                torrent_hashes=self.torrent_hash
            )
        except Exception:
            pass

    def _set_first_last_piece_priority(self):
        """Boost first/last piece priority to speed container header access."""
        try:
            self.qb_client.torrents_set_first_last_piece_priority(
                torrent_hashes=self.torrent_hash, value=True
            )
            return
        except Exception:
            pass
        try:
            self.qb_client.torrents_toggle_first_last_piece_priority(
                torrent_hashes=self.torrent_hash
            )
        except Exception:
            pass

    def _torrent_files(self) -> List[Any]:
        """Return file entries for the active torrent."""
        try:
            return self.qb_client.torrents_files(torrent_hash=self.torrent_hash)
        except Exception:
            return self.qb_client.torrents_files(torrent_hashes=self.torrent_hash)

    def _file_index(self, file_item: Any) -> Optional[int]:
        idx = getattr(file_item, "index", None)
        if idx is None:
            idx = getattr(file_item, "id", None)
        return int(idx) if idx is not None else None

    def _pick_stream_file(self) -> Optional[Any]:
        """Select stream target: preferred relative path, else best media candidate."""
        files = self._torrent_files()
        if not files:
            return None

        preferred = (self.preferred_relative_path or "").lower().lstrip("./")
        if preferred:
            for item in files:
                name = str(getattr(item, "name", "")).replace("\\", "/")
                name_l = name.lower().lstrip("./")
                if name_l == preferred or name_l.endswith("/" + preferred) or name_l.endswith(preferred):
                    return item

        media_rank = {
            ".mp4": 0,
            ".webm": 1,
            ".mov": 2,
            ".m4v": 3,
            ".avi": 4,
            ".mkv": 5,
            ".wmv": 6,
            ".flv": 7,
            ".mp3": 8,
            ".m4a": 9,
            ".aac": 10,
            ".flac": 11,
            ".wav": 12,
            ".ogg": 13,
        }

        candidates = []
        for item in files:
            name = str(getattr(item, "name", "")).lower()
            _, ext = os.path.splitext(name)
            if ext in media_rank:
                size = int(getattr(item, "size", 0) or 0)
                candidates.append((media_rank[ext], -size, item))

        if not candidates:
            return None
        candidates.sort(key=lambda entry: (entry[0], entry[1]))
        return candidates[0][2]

    def _path_is_preferred(self, name: str) -> bool:
        name_l = name.replace("\\", "/").lower().lstrip("./")
        for pref in self.preferred_relative_paths:
            pref_l = pref.lower().lstrip("./")
            if name_l == pref_l or name_l.endswith("/" + pref_l) or name_l.endswith(pref_l):
                return True
        return False

    def _prioritize_selected_file(self, selected_index: int):
        """Download selected + other user-picked media; skip the rest."""
        file_items = self._torrent_files()
        selected_ids = []
        preferred_ids = []
        other_ids = []
        for item in file_items:
            idx = self._file_index(item)
            if idx is None:
                continue
            name = str(getattr(item, "name", ""))
            if idx == selected_index:
                selected_ids.append(idx)
            elif self.preferred_relative_paths and self._path_is_preferred(name):
                preferred_ids.append(idx)
            else:
                other_ids.append(idx)

        if selected_ids:
            try:
                self.qb_client.torrents_file_priority(
                    torrent_hash=self.torrent_hash, file_ids=selected_ids, priority=7
                )
            except Exception:
                pass
        if preferred_ids:
            try:
                self.qb_client.torrents_file_priority(
                    torrent_hash=self.torrent_hash, file_ids=preferred_ids, priority=6
                )
            except Exception:
                pass
        if other_ids and self.preferred_relative_paths:
            try:
                self.qb_client.torrents_file_priority(
                    torrent_hash=self.torrent_hash, file_ids=other_ids, priority=0
                )
            except Exception:
                pass
        elif other_ids and not self.preferred_relative_paths:
            try:
                self.qb_client.torrents_file_priority(
                    torrent_hash=self.torrent_hash, file_ids=other_ids, priority=0
                )
            except Exception:
                pass

    def _buffer_target_bytes(self) -> int:
        """Safer startup buffer: enough header/moov, not a huge wait before first play.

        Overrides via env (no secrets):
          VOXPLAYER_TORRENT_BUFFER_MB   absolute megabytes (optional)
          VOXPLAYER_TORRENT_BUFFER_PCT  percent of file size as float 0–100 (optional)
        """
        if self.stream_file_size <= 0 or not self.stream_file_path:
            return 0
        _, ext = os.path.splitext(self.stream_file_path.lower())
        audio_ext = {
            ".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus", ".ape", ".aiff",
        }
        # Conservative bases: start sooner; sequential + first/last piece cover seeking.
        if ext in audio_ext:
            base = 4 * 1024 * 1024
            soft_cap = 24 * 1024 * 1024
            pct = 0.01
        elif ext == ".mkv":
            base = 24 * 1024 * 1024
            soft_cap = 96 * 1024 * 1024
            pct = 0.015
        else:
            base = 12 * 1024 * 1024
            soft_cap = 64 * 1024 * 1024
            pct = 0.012

        env_mb = os.getenv("VOXPLAYER_TORRENT_BUFFER_MB", "").strip()
        env_pct = os.getenv("VOXPLAYER_TORRENT_BUFFER_PCT", "").strip()
        try:
            if env_pct:
                pct = max(0.001, min(0.10, float(env_pct) / 100.0))
        except ValueError:
            pass
        pct_target = int(self.stream_file_size * pct)
        # Never require more than ~8% of a small file or the soft cap.
        hard_cap = min(soft_cap, max(base, int(self.stream_file_size * 0.08)))
        required = min(max(base, pct_target), hard_cap)
        try:
            if env_mb:
                required = max(1024 * 1024, int(float(env_mb) * 1024 * 1024))
                required = min(required, soft_cap)
        except ValueError:
            pass
        # Tiny files: wait for most of the file.
        if self.stream_file_size < base:
            required = max(1, int(self.stream_file_size * 0.85))
        return required

    def _is_buffer_ready(self):
        """Return whether selected file has enough sequentially downloaded data."""
        if self.stream_file_index is None:
            return False, 0, 0
        # Re-assert sequential + first/last on each poll until ready (client may reset).
        if not getattr(self, "_seq_reasserted", False):
            self._set_sequential_download()
            self._set_first_last_piece_priority()
            self._seq_reasserted = True
        required = self._buffer_target_bytes()
        for item in self._torrent_files():
            idx = self._file_index(item)
            if idx == self.stream_file_index:
                size = int(getattr(item, "size", 0) or 0)
                progress = float(getattr(item, "progress", 0.0) or 0.0)
                downloaded = int(size * progress)
                # Also treat near-complete small remainder as ready.
                if size > 0 and (size - downloaded) <= 512 * 1024 and progress >= 0.95:
                    return True, downloaded, required
                return downloaded >= required, downloaded, required
        return False, 0, required

    def pause_transfer(self):
        """Pause qBittorrent transfer (no upload/download) while keeping the torrent."""
        if not self.qb_client or not self.torrent_hash:
            return
        try:
            self.qb_client.torrents_pause(torrent_hashes=self.torrent_hash)
        except Exception:
            try:
                self.qb_client.torrents_pause(torrent_hash=self.torrent_hash)
            except Exception:
                pass

    def resume_transfer(self):
        """Resume qBittorrent transfer for active playback."""
        if not self.qb_client or not self.torrent_hash:
            return
        try:
            self.qb_client.torrents_resume(torrent_hashes=self.torrent_hash)
        except Exception:
            try:
                self.qb_client.torrents_resume(torrent_hash=self.torrent_hash)
            except Exception:
                pass

    def stop(self):
        """Stop torrent streaming and remove it from the client."""
        self.is_running = False
        if self.qb_client:
            try:
                if self.torrent_hash:
                    self.qb_client.torrents_delete(
                        torrent_hashes=self.torrent_hash, delete_files=True
                    )
            except Exception:
                pass
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.torrent_hash = None
        self.stream_file_path = None

class UpdateChecker(QThread):
    """Thread for checking updates"""
    update_available = pyqtSignal(dict)  # update_info
    check_completed = pyqtSignal(bool)  # has_update

    def __init__(self, current_version: str = "1.0.0"):
        super().__init__()
        self.current_version = current_version
        self.github_repo = "voxhash/voxplayer"
        self.github_api = f"https://api.github.com/repos/{self.github_repo}/releases/latest"

    def run(self):
        """Check for updates"""
        try:
            response = requests.get(
                self.github_api,
                timeout=10,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "VoxPlayer-UpdateChecker",
                },
            )
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data.get("tag_name", "").lstrip("v")

                if latest_version and self._is_newer_version(latest_version, self.current_version):
                    update_info = {
                        "version": latest_version,
                        "download_url": release_data.get("html_url", ""),
                        "release_notes": release_data.get("body", ""),
                        "published_at": release_data.get("published_at", "")
                    }
                    self.update_available.emit(update_info)
                    self.check_completed.emit(True)
                else:
                    self.check_completed.emit(False)
            else:
                self.check_completed.emit(False)

        except Exception as e:
            print(f"Update check failed: {e}")
            self.check_completed.emit(False)

    def _is_newer_version(self, latest: str, current: str) -> bool:
        """Compare version strings"""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]

            # Pad with zeros if needed
            max_len = max(len(latest_parts), len(current_parts))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            current_parts.extend([0] * (max_len - len(current_parts)))

            return latest_parts > current_parts
        except:
            return False

class Settings:
    def __init__(self, org: str, app: str):
        self.settings = QSettings(org, app)

    def save_state(self, state: AppState):
        """Save application state"""
        self.settings.setValue("window_geometry", state.window_geometry)
        self.settings.setValue("theme", state.theme)
        self.settings.setValue("volume", state.volume)
        self.settings.setValue("last_file", state.last_file)
        self.settings.setValue("resume_positions", json.dumps(state.resume_positions or {}))
        self.settings.setValue("audio_output_mode", state.audio_output_mode)
        self.settings.setValue("selected_audio_device", state.selected_audio_device)
        roots = [r for r in (state.library_roots or []) if isinstance(r, str) and r]
        self.settings.setValue("library_roots", json.dumps(roots))
        self.settings.setValue("shuffle_enabled", bool(state.shuffle_enabled))
        mode = state.repeat_mode if state.repeat_mode in ("off", "one", "all") else "off"
        self.settings.setValue("repeat_mode", mode)

    def load_state(self) -> AppState:
        """Load application state"""
        if self.settings.contains("volume"):
            try:
                vol = max(0, min(200, int(self.settings.value("volume"))))
            except (TypeError, ValueError):
                vol = 100
        else:
            vol = 100  # first launch default
        try:
            roots = json.loads(self.settings.value("library_roots", "[]"))
            if not isinstance(roots, list):
                roots = []
        except (TypeError, ValueError, json.JSONDecodeError):
            roots = []
        shuffle_raw = self.settings.value("shuffle_enabled", False)
        if isinstance(shuffle_raw, str):
            shuffle = shuffle_raw.strip().lower() in {"1", "true", "yes"}
        else:
            shuffle = bool(shuffle_raw)
        repeat = str(self.settings.value("repeat_mode", "off") or "off").lower()
        if repeat not in ("off", "one", "all"):
            repeat = "off"
        raw_theme = str(self.settings.value("theme", "ember") or "ember").strip()
        # Migrate legacy dark/light keys to the Ember bundled palette.
        if raw_theme in ("dark", "light", ""):
            raw_theme = "ember"
        return AppState(
            window_geometry=self.settings.value("window_geometry"),
            theme=raw_theme,
            volume=vol,
            last_file=self.settings.value("last_file", ""),
            resume_positions=json.loads(self.settings.value("resume_positions", "{}")),
            audio_output_mode=self.settings.value("audio_output_mode", "default"),
            selected_audio_device=self.settings.value("selected_audio_device", ""),
            library_roots=roots,
            shuffle_enabled=shuffle,
            repeat_mode=repeat,
        )

class PlayerControls(TransportBar):
    """Backward-compatible name for the modern bottom transport bar."""
    pass


class PlaylistWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()

    def setup_ui(self):
        self.setSelectionMode(self.SelectionMode.SingleSelection)
        self.setAcceptDrops(True)
        self.setDragDropMode(self.DragDropMode.DropOnly)  # Allow external drops
        self.itemDoubleClicked.connect(self.item_double_clicked)

    def item_double_clicked(self, item):
        if hasattr(self.parent_window, 'play_selected_item'):
            self.parent_window.play_selected_item()

    def add_media_file(self, file_path):
        """Add a media file to the playlist"""
        filename = os.path.basename(file_path) if file_path and "://" not in file_path else file_path

        # Create custom widget for playlist item
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(4, 2, 4, 2)
        item_layout.setSpacing(4)

        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(12, 12)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 100, 100, 0.8);
                border: 1px solid rgba(255, 100, 100, 1.0);
                border-radius: 6px;
                color: white;
                font-size: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 100, 100, 1.0);
                border-color: #FF6666;
            }
        """)
        remove_btn.clicked.connect(lambda: self.remove_item_by_file(file_path))

        # File name label
        name_label = QLabel(filename)
        name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 9px;
                background: transparent;
                border: none;
            }
        """)
        name_label.setWordWrap(True)

        # Add to layout
        item_layout.addWidget(remove_btn)
        item_layout.addWidget(name_label)
        item_layout.addStretch()

        # Create list item
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        item.setSizeHint(item_widget.sizeHint())

        # Add to list
        self.addItem(item)
        self.setItemWidget(item, item_widget)

    def remove_item_by_file(self, file_path):
        """Remove an item from the playlist by file path"""
        for i in range(self.count()):
            item = self.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == file_path:
                # If this is the currently playing file, stop playback
                if hasattr(self.parent_window, 'app_state') and self.parent_window.app_state.last_file == file_path:
                    if hasattr(self.parent_window, 'stop_playback'):
                        self.parent_window.stop_playback()

                # Remove the item
                self.takeItem(i)
                break

    def get_current_file(self):
        """Get the currently selected file path"""
        current_item = self.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None

    def find_file_index(self, file_path):
        """Find the index of a file in the playlist"""
        for i in range(self.count()):
            item = self.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == file_path:
                return i
        return None

    def get_file_at_index(self, index):
        """Get the file path at a specific index"""
        if 0 <= index < self.count():
            item = self.item(index)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            # Check if any of the URLs are supported media files or directories
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if (self.parent_window.is_supported_media_file(file_path) or
                    os.path.isdir(file_path)):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        """Handle drop event with enhanced support for multiple files/folders"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            media_files = []
            folders_processed = 0
            files_processed = 0

            # Process all dropped items
            for url in urls:
                file_path = url.toLocalFile()
                if os.path.isdir(file_path):
                    # Handle folder - find all media files recursively
                    folder_files = self.parent_window.find_media_files_in_folder(file_path)
                    media_files.extend(folder_files)
                    folders_processed += 1
                    if folder_files:
                        self.parent_window.status_bar.showMessage(f"Scanning folder: {os.path.basename(file_path)} ({len(folder_files)} files found)", 2000)
                elif self.parent_window.is_supported_media_file(file_path):
                    # Handle individual media file
                    media_files.append(file_path)
                    files_processed += 1

            if media_files:
                # Remove duplicates while preserving order
                seen = set()
                unique_media_files = []
                for file_path in media_files:
                    if file_path not in seen:
                        seen.add(file_path)
                        unique_media_files.append(file_path)

                # Sort files naturally for better organization
                unique_media_files.sort()

                # Clear current playlist and add all files
                self.clear()
                for file_path in unique_media_files:
                    self.add_media_file(file_path)

                # Load and auto-play the first file
                if unique_media_files:
                    self.parent_window.load_media(unique_media_files[0])
                    self.setCurrentRow(0)

                    # Auto-start playback
                    QTimer.singleShot(100, self.parent_window._engine_play)

                    # Show comprehensive status message
                    status_parts = []
                    if files_processed > 0:
                        status_parts.append(f"{files_processed} file{'s' if files_processed != 1 else ''}")
                    if folders_processed > 0:
                        status_parts.append(f"{folders_processed} folder{'s' if folders_processed != 1 else ''}")

                    status_msg = f"Loaded {len(unique_media_files)} media files from {', '.join(status_parts)}"
                    self.parent_window.status_bar.showMessage(status_msg, 5000)

                event.acceptProposedAction()
                return

        event.ignore()


class SubtitleManager:
    """Overlay cues for SRT/VTT/ASS; prefer native libvlc for ASS/SSA when available."""

    def __init__(self, video_widget, parent=None):
        self.video_widget = video_widget
        self.parent_window = parent
        self.subtitle_label = QLabel("")
        self.subtitle_label.setParent(video_widget)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.subtitle_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 150);
                padding: 5px;
                border-radius: 3px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        self.subtitle_label.hide()
        self.current_subtitles = []
        self.current_position = 0
        self._native_path = ""
        self._overlay_disabled = False

    def clear(self) -> None:
        self.current_subtitles = []
        self._native_path = ""
        self._overlay_disabled = False
        self.subtitle_label.hide()

    def load_subtitles(self, file_path: str) -> bool:
        """Load SRT / WebVTT / ASS / SSA sidecar."""
        from .subtitles import load_subtitle_file

        if not file_path or not os.path.isfile(file_path):
            return False
        ext = os.path.splitext(file_path)[1].lower()
        # Prefer native engine rendering for ASS/SSA (full styling).
        if ext in {".ass", ".ssa"} and self._try_native_subtitle(file_path):
            self._overlay_disabled = True
            self.current_subtitles = []
            self._native_path = file_path
            self.subtitle_label.hide()
            return True
        try:
            self.current_subtitles = load_subtitle_file(file_path)
            self._overlay_disabled = False
            self._native_path = ""
            # Also hand the file to libvlc when possible (SRT/VTT).
            self._try_native_subtitle(file_path)
            return bool(self.current_subtitles)
        except Exception as e:
            print(f"Error loading subtitles: {e}")
            return False

    def _try_native_subtitle(self, file_path: str) -> bool:
        win = self.parent_window
        engine = getattr(win, "engine", None) if win is not None else None
        player = getattr(engine, "_player", None) if engine is not None else None
        if player is None:
            return False
        try:
            player.video_set_subtitle_file(file_path)
            return True
        except Exception:
            return False

    def update_position(self, position_ms):
        """Update overlay subtitle display based on current position."""
        self.current_position = position_ms
        if self._overlay_disabled or not self.current_subtitles:
            if not self._overlay_disabled:
                self.subtitle_label.hide()
            return
        current_subtitle = None
        for subtitle in self.current_subtitles:
            if subtitle["start"] <= position_ms <= subtitle["end"]:
                current_subtitle = subtitle
                break
        if current_subtitle:
            self.subtitle_label.setText(str(current_subtitle["text"]))
            self.subtitle_label.show()
        else:
            self.subtitle_label.hide()

    def position_subtitle_label(self):
        """Position subtitle label at bottom of video"""
        if self.video_widget:
            rect = self.video_widget.rect()
            self.subtitle_label.setGeometry(
                10, rect.height() - 60,
                rect.width() - 20, 50
            )

class VoxPlayerMainWindow(QMainWindow):
    def __init__(self, file_to_open=None):
        super().__init__()
        self.settings = Settings("VoxPlayer", "VoxHash")
        self.app_state = self.settings.load_state()
        self.controls_visible = True
        self.mouse_timer = None
        self.playlist_visible = False  # Hidden by default
        self.playlist_timer = None
        self.file_to_open = file_to_open

        # Torrent and update functionality
        self.torrent_streamer = None
        self._torrent_active_paths = set()  # local paths belonging to the active torrent session
        self._pending_torrent_rel_paths: List[str] = []
        self.update_checker = None
        self.current_version = "1.13.0"
        self.thumb_cache = ThumbnailCache()
        self._meta_cache: Dict[str, MediaMetadata] = {}
        self._thumb_map: Dict[str, str] = {}
        self._preview_timer = None
        self._enrich_thread = None
        self.library_index = LibraryIndex.load()
        self._library_watcher: Optional[QFileSystemWatcher] = None
        self._watch_debounce: Optional[QTimer] = None
        self._watch_dirty_roots: Set[str] = set()
        self.podcast_store = PodcastStore()
        self.mpris = MprisController(self)
        self.control_daemon = ControlDaemon()
        # Phase 2: Rust metadata + thumbnail worker pool (optional; falls back to sync Python).
        self.native_workers = NativeMediaWorkers(self)
        if self.native_workers.available:
            self.native_workers.thumb_ready.connect(self._on_native_thumb_ready)
            self.native_workers.tags_ready.connect(self._on_native_tags_ready)
        self.playlist_store = PlaylistStore()
        self._stage_expanded = False
        self._shell_page = "home"
        self._fav_selected = PlaylistStore.FAVORITES
        self._close_to_tray = True
        self.tray_icon = None

        # Audio device detection
        self.current_audio_device = None
        self.audio_device_timer = None
        self.available_audio_devices = []
        self.audio_device_menu = None

        # Palette must be live before widgets paint (empty-state inline colors, etc.).
        apply_theme_id(self.app_state.theme or "ember")
        self.setup_ui()
        self.setup_media_player()
        self.setup_shortcuts()
        self.setup_timers()
        self.setup_drag_drop()
        self.setup_auto_update()
        self.apply_theme()
        self.setup_icon()
        self.setup_system_tray()

        # Initialize audio device
        self.update_audio_device()

        # Load file if provided via command line
        if self.file_to_open:
            # Use QTimer to ensure the UI is fully loaded before loading the file
            QTimer.singleShot(100, lambda: self.load_and_play_media(self.file_to_open))

    def setup_ui(self):
        self.setWindowTitle("VoxPlayer")
        self.setMinimumSize(960, 600)

        if self.app_state.window_geometry:
            self.restoreGeometry(self.app_state.window_geometry)
        else:
            self.resize(1280, 800)

        self.library_paths = []
        self._shuffle_order: List[int] = []
        self._shuffle_pos = 0
        self.shell_mode = "home"
        self.now_playing_visible = True
        self._home_filter = "all"
        self._home_query = ""

        shell = QWidget()
        shell.setObjectName("ShellRoot")
        self.setCentralWidget(shell)
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.left_rail = LeftRail(self)
        self.left_rail.home_requested.connect(lambda: self.show_shell_page("home"))
        self.left_rail.library_requested.connect(lambda: self.show_shell_page("library"))
        self.left_rail.browse_requested.connect(lambda: self.show_shell_page("browse"))
        self.left_rail.favorites_requested.connect(lambda: self.show_shell_page("favorites"))
        self.left_rail.open_file_requested.connect(self.open_file)
        self.left_rail.open_folder_requested.connect(self.open_folder)
        self.left_rail.torrent_requested.connect(self.open_torrent_file)
        body_layout.addWidget(self.left_rail)

        center = QWidget()
        center.setObjectName("CenterStage")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.center_stack = QStackedWidget()
        self.home_view = HomeView(self)
        self.home_view.media_activated.connect(self.load_and_play_media)
        self.home_view.filter_changed.connect(self.apply_home_filter)
        self.home_view.search_changed.connect(self.apply_home_search)
        self.home_view.media_context.connect(self.show_library_context_menu)
        self.home_view.facet_selected.connect(self.apply_facet_bucket)
        self.home_view.collection_selected.connect(self.show_favorites_library)
        self.home_view.files_dropped.connect(self.handle_shell_drop)

        self.stage_page = QWidget()
        stage_layout = QVBoxLayout(self.stage_page)
        stage_layout.setContentsMargins(12, 12, 12, 8)
        stage_layout.setSpacing(0)
        # Plain QWidget host for native window-ID video embed (QVideoWidget can paint black over VO).
        self.video_widget = QWidget()
        self.video_widget.setObjectName("VideoSurface")
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True)
        self.video_widget.setStyleSheet("#VideoSurface { background-color: #000000; }")
        self.video_widget.setAcceptDrops(True)
        self.video_widget.mouseDoubleClickEvent = lambda event: self.toggle_fullscreen()
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_widget.setMinimumSize(160, 90)
        stage_layout.addWidget(self.video_widget)
        self.center_stack.addWidget(self.home_view)
        self.center_stack.addWidget(self.stage_page)
        center_layout.addWidget(self.center_stack, 1)
        body_layout.addWidget(center, 1)

        self.now_playing = NowPlayingPanel(self)
        self.now_playing.art_clicked.connect(self.expand_now_playing_view)
        self.now_playing.expand_requested.connect(self.expand_now_playing_view)
        self.now_playing.minimize_requested.connect(self.minimize_now_playing_view)
        self.now_playing.more_requested.connect(self.show_now_playing_more_menu)
        self.now_playing.queue_play_requested.connect(self.load_and_play_media)
        self.now_playing.queue_remove_requested.connect(self.remove_from_up_next)
        self.now_playing.queue_clear_requested.connect(self.clear_up_next_and_stop)
        self.now_playing.add_to_playlist_requested.connect(self.toggle_or_add_playlist_path)
        self.now_playing.files_dropped.connect(self.handle_shell_drop)
        self.now_playing.favorite_check = lambda p: self.playlist_store.contains(
            PlaylistStore.FAVORITES, p
        )
        body_layout.addWidget(self.now_playing)

        shell_layout.addWidget(body, 1)

        self.controls = TransportBar(self)
        self.controls.files_dropped.connect(self.handle_shell_drop)
        shell_layout.addWidget(self.controls)

        # Up next data model only — no right-side Queue dock (Up next lives in Now Playing).
        self.playlist = PlaylistWidget(self)
        self.playlist.hide()
        self.playlist_visible = False

        self.subtitle_manager = SubtitleManager(self.video_widget, self)

        self.timeline_preview = QLabel("")
        self.timeline_preview.setParent(self.video_widget)
        self.timeline_preview.setStyleSheet(
            f"QLabel {{ background-color: rgba(11,15,20,220); border: 1px solid {COLORS['accent']};"
            f" border-radius: 8px; color: white; font-size: 12px; font-weight: bold; padding: 8px; }}"
        )
        self.timeline_preview.hide()
        self.timeline_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self.create_menu_bar()
        self.setMouseTracking(True)
        self.video_widget.setMouseTracking(True)
        self.controls.setMouseTracking(True)

        if self.app_state.last_file and os.path.exists(self.app_state.last_file):
            self._register_library_path(self.app_state.last_file)
        self._restore_library_roots()
        self._setup_library_watcher()
        self.refresh_home_grid()
        if hasattr(self, "controls"):
            self.controls.sync_playback_modes(
                bool(self.app_state.shuffle_enabled),
                str(self.app_state.repeat_mode or "off"),
            )
        self._setup_mpris_and_daemon()

    def show_shell_page(self, page: str):
        self._shell_page = page
        if page == "stage":
            self.shell_mode = "stage"
            self._stage_expanded = True
            self.center_stack.setCurrentWidget(self.stage_page)
            if hasattr(self, "engine") and self.engine is not None:
                # Soft rebind keeps playback; hard only if WID was lost.
                QTimer.singleShot(50, lambda: self.engine.rebind_video_widget(hard=False))
            return
        self._stage_expanded = False
        self.shell_mode = "home"
        self.center_stack.setCurrentWidget(self.home_view)
        if page == "browse":
            self.left_rail.set_active("browse")
            self.home_view.set_browse_mode(True)
            self.home_view.set_facets_enabled(True)
            self.home_view.clear_collections()
            self.refresh_home_grid()
            self.refresh_facets()
        elif page == "favorites":
            self.left_rail.set_active("favorites")
            self.home_view.set_browse_mode(False)
            self.home_view.set_facets_enabled(False)
            self.show_favorites_library()
        elif page in ("home", "library"):
            self.left_rail.set_active("library" if page == "library" else "home")
            self.home_view.set_browse_mode(False)
            self.home_view.set_facets_enabled(True)
            self.home_view.clear_collections()
            self.refresh_home_grid()
            self.refresh_facets()
        else:
            self.left_rail.set_active("home")
            self.home_view.set_browse_mode(False)
            self.home_view.set_facets_enabled(True)
            self.home_view.clear_collections()
            self.refresh_home_grid()
            self.refresh_facets()

    def is_video_path(self, path: str) -> bool:
        if not path:
            return False
        return os.path.splitext(path)[1].lower() in FACET_VIDEO_EXT

    def expand_now_playing_view(self):
        """Show center stage for video (or any media when user expands via art)."""
        path = getattr(self.app_state, "last_file", "") or ""
        if not path:
            self.status_bar.showMessage("Nothing playing to expand.", 2500)
            return
        self.show_shell_page("stage")
        self.toggle_now_playing(True)
        self.status_bar.showMessage("Now Playing expanded — Esc to minimize", 3000)

    def minimize_now_playing_view(self):
        """Return to library; keep playback running."""
        self._stage_expanded = False
        if self.isFullScreen():
            self.showNormal()
        self.show_shell_page("home")
        self.toggle_now_playing(True)

    def focus_queue_panel(self):
        """Focus Up next in the Now Playing panel (Queue dock removed)."""
        self.toggle_now_playing(True)

    def toggle_now_playing(self, force=None):
        visible = (not self.now_playing_visible) if force is None else bool(force)
        self.now_playing.setVisible(visible)
        self.now_playing_visible = visible

    def _register_library_path(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            return
        if file_path not in self.library_paths:
            self.library_paths.insert(0, file_path)

    def _remember_library_root(self, folder_path: str) -> None:
        """Persist an Open Folder root so the library reloads next launch."""
        if not folder_path:
            return
        root = os.path.abspath(folder_path)
        if not os.path.isdir(root):
            return
        roots = list(self.app_state.library_roots or [])
        if root in roots:
            roots.remove(root)
        roots.insert(0, root)
        self.app_state.library_roots = roots[:32]
        self.settings.save_state(self.app_state)
        self._incremental_scan_root(root, quiet=True)
        self.library_index.save()
        self._watch_library_root(root)

    def _restore_library_roots(self) -> None:
        """Re-index persisted library folder roots via incremental native scan."""
        roots = [r for r in (self.app_state.library_roots or []) if isinstance(r, str)]
        alive: List[str] = []
        added_total = 0
        removed_total = 0
        for root in roots:
            if not os.path.isdir(root):
                continue
            alive.append(os.path.abspath(root))
            current, added, removed = self._incremental_scan_root(root, quiet=True)
            for path in current:
                if path and path not in self.library_paths:
                    self.library_paths.append(path)
            added_total += len(added)
            removed_total += len(removed)
            for path in removed:
                if path in self.library_paths:
                    self.library_paths.remove(path)
        if alive != list(self.app_state.library_roots or []):
            self.app_state.library_roots = alive
            self.settings.save_state(self.app_state)
        self.library_index.save()
        if hasattr(self, "status_bar") and (added_total or removed_total):
            backend = scan_backend_name() or "python"
            self.status_bar.showMessage(
                f"Library index ({backend}): +{added_total} / −{removed_total}",
                4000,
            )

    def _incremental_scan_root(
        self, root: str, *, quiet: bool = False
    ) -> Tuple[List[str], List[str], List[str]]:
        """Scan one root with fingerprinting; uses native vox_scan when built."""
        root = os.path.abspath(root)

        def _walker(folder: str) -> List[str]:
            return self.find_media_files_in_folder(folder)

        current, added, removed = self.library_index.scan_root(
            root, extensions=DEFAULT_EXTS, walker=_walker
        )
        if not quiet and hasattr(self, "status_bar"):
            backend = scan_backend_name() or "python"
            self.status_bar.showMessage(
                f"Rescan {os.path.basename(root)} ({backend}): "
                f"+{len(added)} / −{len(removed)}",
                3500,
            )
        return current, added, removed

    def _setup_library_watcher(self) -> None:
        """Watch persisted library roots; debounce incremental re-scans."""
        if self._library_watcher is None:
            self._library_watcher = QFileSystemWatcher(self)
            self._library_watcher.directoryChanged.connect(self._on_library_path_changed)
            self._library_watcher.fileChanged.connect(self._on_library_path_changed)
        if self._watch_debounce is None:
            self._watch_debounce = QTimer(self)
            self._watch_debounce.setSingleShot(True)
            self._watch_debounce.setInterval(900)
            self._watch_debounce.timeout.connect(self._flush_library_watch)
        # Periodic catch-up for nested dirs inotify may miss
        if not hasattr(self, "_watch_poll") or self._watch_poll is None:
            self._watch_poll = QTimer(self)
            self._watch_poll.setInterval(60_000)
            self._watch_poll.timeout.connect(self._poll_library_roots)
            self._watch_poll.start()
        for root in list(self.app_state.library_roots or []):
            self._watch_library_root(root)

    def _watch_library_root(self, root: str) -> None:
        if not root or not os.path.isdir(root):
            return
        if self._library_watcher is None:
            self._setup_library_watcher()
        watched = set(self._library_watcher.directories())
        abs_root = os.path.abspath(root)
        if abs_root not in watched:
            self._library_watcher.addPath(abs_root)
        # Watch one level of subdirs for better nested coverage without flooding.
        try:
            for name in os.listdir(abs_root)[:64]:
                sub = os.path.join(abs_root, name)
                if os.path.isdir(sub) and sub not in watched:
                    self._library_watcher.addPath(sub)
        except OSError:
            pass

    def _on_library_path_changed(self, path: str) -> None:
        if not path:
            return
        abs_path = os.path.abspath(path)
        roots = [os.path.abspath(r) for r in (self.app_state.library_roots or [])]
        hit = None
        for root in roots:
            if abs_path == root or abs_path.startswith(root + os.sep):
                hit = root
                break
        if hit is None:
            # fileChanged may report a media file; map to nearest root
            for root in roots:
                if abs_path.startswith(root + os.sep):
                    hit = root
                    break
        if hit:
            self._watch_dirty_roots.add(hit)
            if self._watch_debounce is not None:
                self._watch_debounce.start()

    def _poll_library_roots(self) -> None:
        for root in list(self.app_state.library_roots or []):
            if os.path.isdir(root):
                self._watch_dirty_roots.add(os.path.abspath(root))
        if self._watch_dirty_roots and self._watch_debounce is not None:
            self._watch_debounce.start()

    def _flush_library_watch(self) -> None:
        dirty = list(self._watch_dirty_roots)
        self._watch_dirty_roots.clear()
        if not dirty:
            return
        changed = False
        for root in dirty:
            current, added, removed = self._incremental_scan_root(root)
            for path in added:
                if path not in self.library_paths:
                    self.library_paths.insert(0, path)
                    changed = True
            for path in removed:
                if path in self.library_paths:
                    self.library_paths.remove(path)
                    changed = True
            # Ensure root still watched (new subdirs)
            self._watch_library_root(root)
        self.library_index.save()
        if changed:
            self.refresh_home_grid()
            self.refresh_facets()

    def refresh_home_grid(self, filter_name: str = None, query: str = None):
        filter_name = (filter_name or getattr(self, "_home_filter", "all")).lower()
        query = (query if query is not None else getattr(self, "_home_query", "")).lower()
        self._home_filter = filter_name
        self._home_query = query
        video_ext = FACET_VIDEO_EXT
        audio_ext = FACET_AUDIO_EXT
        items = list(self.library_paths)
        if hasattr(self, "playlist"):
            for i in range(self.playlist.count()):
                p = self.playlist.get_file_at_index(i)
                if p and p not in items:
                    items.append(p)
        filtered = []
        for path in items:
            ext = os.path.splitext(path)[1].lower()
            if filter_name == "video" and ext not in video_ext:
                continue
            if filter_name == "audio" and ext not in audio_ext:
                continue
            if query and query not in os.path.basename(path).lower():
                continue
            filtered.append(path)
        if filter_name == "recent":
            filtered = filtered[:24]
        thumbs = {}
        for path in filtered[:64]:
            cached = self._thumb_map.get(path) or get_thumbnail_path(path)
            if cached:
                thumbs[path] = cached
                self._thumb_map[path] = cached
            else:
                self._queue_library_media_work(path)
        self.home_view.set_items(filtered, thumbnails=thumbs)
        self.home_view.hint.setText(f"{len(filtered)} items")
        if getattr(self.home_view, "_browse_mode", False):
            self.refresh_facets()

    def apply_home_filter(self, name: str):
        self.home_view._filter_name = (name or "all").lower()
        if getattr(self, "_shell_page", "") == "favorites":
            self.show_favorites_library(getattr(self, "_fav_selected", None))
            return
        self.refresh_home_grid(filter_name=name)
        self.refresh_facets()

    def apply_home_search(self, text: str):
        if getattr(self, "_shell_page", "") == "favorites":
            self.show_favorites_library(getattr(self, "_fav_selected", None))
            return
        self.refresh_home_grid(query=text)

    def refresh_facets(self):
        if getattr(self, "_shell_page", "") == "favorites":
            return
        items = list(getattr(self, "library_paths", []) or [])
        stats = getattr(self, "library_index", None)
        facets = group_library(
            items,
            self._meta_cache,
            stats_by_path=stats.stats if stats else None,
        )
        self.home_view.set_facets(facets)

    def apply_facet_bucket(self, facet_key: str, bucket: str):
        stats = getattr(self, "library_index", None)
        facets = group_library(
            list(getattr(self, "library_paths", []) or []),
            self._meta_cache,
            stats_by_path=stats.stats if stats else None,
        )
        paths = facets.get(facet_key, {}).get(bucket, [])
        thumbs = {}
        for path in paths[:64]:
            cached = self._thumb_map.get(path) or get_thumbnail_path(path)
            if cached:
                thumbs[path] = cached
            else:
                self._queue_library_media_work(path)
        self.home_view.set_items(paths, thumbnails=thumbs)
        self.home_view.hint.setText(f"{bucket}: {len(paths)} items")
        label_map = {
            "year": "Year",
            "genre": "Genre",
            "artist": "Artist",
            "album": "Album",
            "movies": "Movies",
            "tv": "TV Shows",
            "recently": "Recently played",
            "never": "Never played",
            "most_played": "Most played",
        }
        self.home_view.title_label.setText(f"Browse · {label_map.get(facet_key, facet_key.title())}")

    def show_favorites_library(self, playlist_name: str = None):
        names = self.playlist_store.names()
        selected = playlist_name or getattr(self, "_fav_selected", None) or PlaylistStore.FAVORITES
        if selected not in names:
            selected = PlaylistStore.FAVORITES if PlaylistStore.FAVORITES in names else (names[0] if names else PlaylistStore.FAVORITES)
        self._fav_selected = selected
        self.home_view.set_collections(names, selected)
        paths = [p for p in self.playlist_store.get(selected) if os.path.isfile(p)]
        filt = (getattr(self.home_view, "_filter_name", "all") or "all").lower()
        query = (getattr(self, "_home_query", "") or "").lower()
        if filt == "video":
            paths = [p for p in paths if os.path.splitext(p)[1].lower() in FACET_VIDEO_EXT]
        elif filt == "audio":
            paths = [p for p in paths if os.path.splitext(p)[1].lower() in FACET_AUDIO_EXT]
        elif filt == "recent":
            paths = paths[:24]
        if query:
            paths = [p for p in paths if query in os.path.basename(p).lower()]
        thumbs = {}
        for p in paths[:64]:
            cached = self._thumb_map.get(p) or get_thumbnail_path(p)
            if cached:
                thumbs[p] = cached
            else:
                self._queue_library_media_work(p)
        self.home_view.set_items(paths, thumbnails=thumbs)
        self.home_view.title_label.setText(
            "Favorites & playlists" if selected == PlaylistStore.FAVORITES else selected
        )
        self.home_view.hint.setText(f"{len(paths)} saved items")

    def show_library_context_menu(self, path: str, global_pos):
        if not path:
            return
        menu = QMenu(self)
        play = menu.addAction("Play")
        add_q = menu.addAction("Add to Up next")
        in_fav = self.playlist_store.contains(PlaylistStore.FAVORITES, path)
        fav = menu.addAction("Remove from Favorites" if in_fav else "Add to Favorites")
        save_pl = menu.addAction("Save to playlist…")
        remove_pl = None
        current_pl = getattr(self, "_fav_selected", None)
        if (
            getattr(self, "_shell_page", "") == "favorites"
            and current_pl
            and current_pl != PlaylistStore.FAVORITES
            and self.playlist_store.contains(current_pl, path)
        ):
            remove_pl = menu.addAction(f"Remove from {current_pl}")
        chosen = menu.exec(global_pos)
        if chosen == play:
            self.load_and_play_media(path)
        elif chosen == add_q:
            self.add_to_up_next(path)
        elif chosen == fav:
            if in_fav:
                self.playlist_store.remove(PlaylistStore.FAVORITES, path)
                self.status_bar.showMessage(
                    f"Removed {os.path.basename(path)} from Favorites", 3000
                )
                if getattr(self, "_shell_page", "") == "favorites":
                    self.show_favorites_library()
            else:
                self.add_path_to_named_playlist(path, PlaylistStore.FAVORITES)
        elif chosen == save_pl:
            self.save_path_to_playlist_picker(path)
        elif remove_pl is not None and chosen == remove_pl and current_pl:
            self.playlist_store.remove(current_pl, path)
            self.status_bar.showMessage(
                f"Removed {os.path.basename(path)} from {current_pl}", 3000
            )
            self.show_favorites_library(current_pl)

    def save_path_to_playlist_picker(self, path: str):
        """Pick an existing playlist or create a new one, then add path."""
        if not path:
            return
        existing = [n for n in self.playlist_store.names() if n != PlaylistStore.FAVORITES]
        choices = existing + ["Create new…"]
        chosen, ok = QInputDialog.getItem(
            self,
            "Save to playlist",
            "Choose playlist:",
            choices,
            0,
            False,
        )
        if not ok or not chosen:
            return
        if chosen == "Create new…":
            name, ok2 = QInputDialog.getText(self, "New playlist", "Playlist name:")
            if not ok2 or not name.strip():
                return
            self.add_path_to_named_playlist(path, name.strip())
        else:
            self.add_path_to_named_playlist(path, chosen)

    def add_to_up_next(self, path: str):
        if not path or not os.path.exists(path):
            return
        existing = [self.playlist.get_file_at_index(i) for i in range(self.playlist.count())]
        if path not in existing:
            self.playlist.add_media_file(path)
        self._sync_now_playing_queue()
        self.status_bar.showMessage(f"Added to Up next: {os.path.basename(path)}", 2500)

    def remove_from_up_next(self, path: str):
        if hasattr(self, "playlist"):
            self.playlist.remove_item_by_file(path)
        self._sync_now_playing_queue()
        self.status_bar.showMessage(f"Removed from Up next: {os.path.basename(path)}", 2500)
        self._maybe_release_torrent_after_queue_change()

    def clear_up_next_and_stop(self):
        self.stop_playback()
        self._stop_torrent_session(silent=True)
        if hasattr(self, "playlist"):
            self.playlist.clear()
        self.app_state.last_file = ""
        if hasattr(self, "now_playing"):
            self.now_playing.update_now_playing(None)
            self.now_playing.set_queue([])
            self.now_playing.engine_label.setText("Engine: —")
        if hasattr(self, "controls"):
            self.controls.set_track_meta("VoxPlayer", "Ready")
            self.controls.set_track_art()
            self.controls.update_time(0, 0)
            self.controls.update_seek_position(0)
            self.controls.btn_play.setText("▶")
        self.setWindowTitle("VoxPlayer")
        if self.isFullScreen():
            self.showNormal()
        self._stage_expanded = False
        self.show_shell_page("home")
        self.toggle_now_playing(True)
        self.status_bar.showMessage("Cleared Up next and stopped playback.", 3000)

    def _sync_now_playing_queue(self):
        if not hasattr(self, "now_playing") or not hasattr(self, "playlist"):
            return
        paths = [self.playlist.get_file_at_index(i) for i in range(self.playlist.count())]
        self.now_playing.set_queue([p for p in paths if p], getattr(self.app_state, "last_file", None))

    def toggle_or_add_playlist_path(self, path: str, playlist_name: str):
        """Add path, or remove when Favorites is already saved (context-menu toggle)."""
        if not path:
            return
        if (
            playlist_name == PlaylistStore.FAVORITES
            and self.playlist_store.contains(PlaylistStore.FAVORITES, path)
        ):
            self.playlist_store.remove(PlaylistStore.FAVORITES, path)
            self.status_bar.showMessage(
                f"Removed {os.path.basename(path)} from Favorites", 3000
            )
            if getattr(self, "_shell_page", "") == "favorites":
                self.show_favorites_library()
            return
        self.add_path_to_named_playlist(path, playlist_name)

    def add_path_to_named_playlist(self, path: str, playlist_name: str):
        if not path:
            return
        added = self.playlist_store.add(playlist_name, path)
        msg = "Added" if added else "Already in"
        self.status_bar.showMessage(f"{msg} {os.path.basename(path)} → {playlist_name}", 3000)
        if getattr(self, "_shell_page", "") == "favorites":
            self.show_favorites_library(playlist_name)

    def show_now_playing_more_menu(self, global_pos):
        path = getattr(self.app_state, "last_file", "") or ""
        menu = QMenu(self)
        expand = menu.addAction("Expand Now Playing")
        minimize = menu.addAction("Minimize Now Playing")
        menu.addSeparator()
        in_fav = bool(path) and self.playlist_store.contains(PlaylistStore.FAVORITES, path)
        fav = menu.addAction(
            "Remove current from Favorites" if in_fav else "Add current to Favorites"
        )
        add_q = menu.addAction("Add current to Up next")
        clear = menu.addAction("Clear Up next and stop")
        menu.addSeparator()
        tray = menu.addAction("Minimize to tray")
        chosen = menu.exec(global_pos)
        if chosen == expand:
            self.expand_now_playing_view()
        elif chosen == minimize:
            self.minimize_now_playing_view()
        elif chosen == fav and path:
            self.toggle_or_add_playlist_path(path, PlaylistStore.FAVORITES)
        elif chosen == add_q and path:
            self.add_to_up_next(path)
        elif chosen == clear:
            self.clear_up_next_and_stop()
        elif chosen == tray:
            self.hide_to_tray()

    def create_menu_bar(self):
        menubar = self.menuBar()

        # Media menu (renamed from File)
        media_menu = menubar.addMenu("&Media")

        open_action = QAction("&Open File...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        media_menu.addAction(open_action)

        open_files_action = QAction("Open &Files...", self)
        open_files_action.setShortcut("Ctrl+Shift+O")
        open_files_action.triggered.connect(self.open_files)
        media_menu.addAction(open_files_action)

        open_folder_action = QAction("Open &Folder...", self)
        open_folder_action.setShortcut("Ctrl+Shift+F")
        open_folder_action.triggered.connect(self.open_folder)
        media_menu.addAction(open_folder_action)

        media_menu.addSeparator()

        # Torrent submenu
        torrent_menu = media_menu.addMenu("&Torrent")

        open_magnet_action = QAction("Open &Magnet Link", self)
        open_magnet_action.setShortcut("Ctrl+M")
        open_magnet_action.triggered.connect(self.open_magnet_link)
        torrent_menu.addAction(open_magnet_action)

        open_torrent_action = QAction("Open &Torrent File", self)
        open_torrent_action.setShortcut("Ctrl+T")
        open_torrent_action.triggered.connect(self.open_torrent_file)
        torrent_menu.addAction(open_torrent_action)

        webui_setup_action = QAction("Web UI &Setup Guide…", self)
        webui_setup_action.triggered.connect(self.show_qbittorrent_webui_setup)
        torrent_menu.addAction(webui_setup_action)

        stop_torrent_action = QAction("&Stop Torrent", self)
        stop_torrent_action.setShortcut("Ctrl+Shift+T")
        stop_torrent_action.triggered.connect(self.stop_torrent)
        torrent_menu.addAction(stop_torrent_action)

        # Podcasts submenu
        podcast_menu = media_menu.addMenu("&Podcasts")
        sub_pod_action = QAction("&Subscribe to Feed…", self)
        sub_pod_action.triggered.connect(self.subscribe_podcast_feed)
        podcast_menu.addAction(sub_pod_action)
        refresh_pod_action = QAction("&Refresh Feeds", self)
        refresh_pod_action.triggered.connect(self.refresh_podcast_feeds)
        podcast_menu.addAction(refresh_pod_action)
        browse_pod_action = QAction("&Browse / Download Episodes…", self)
        browse_pod_action.triggered.connect(self.browse_podcast_episodes)
        podcast_menu.addAction(browse_pod_action)
        open_pod_dir_action = QAction("Open Downloads &Folder", self)
        open_pod_dir_action.triggered.connect(lambda: webbrowser.open(QUrl.fromLocalFile(podcasts_dir()).toString()))
        podcast_menu.addAction(open_pod_dir_action)

        media_menu.addSeparator()

        # Playlists submenu
        playlists_menu = media_menu.addMenu("&Playlists")

        import_playlist_action = QAction("&Import Playlist...", self)
        import_playlist_action.setShortcut("Ctrl+I")
        import_playlist_action.triggered.connect(self.import_playlist)
        playlists_menu.addAction(import_playlist_action)

        export_playlist_action = QAction("&Export Playlist...", self)
        export_playlist_action.setShortcut("Ctrl+E")
        export_playlist_action.triggered.connect(self.export_playlist)
        playlists_menu.addAction(export_playlist_action)

        playlists_menu.addSeparator()

        clear_playlist_action = QAction("&Clear Playlist", self)
        clear_playlist_action.setShortcut("Ctrl+Shift+C")
        clear_playlist_action.triggered.connect(self.clear_up_next_and_stop)
        playlists_menu.addAction(clear_playlist_action)

        fav_action = QAction("Toggle Current in &Favorites", self)
        fav_action.triggered.connect(
            lambda: self.toggle_or_add_playlist_path(
                getattr(self.app_state, "last_file", "") or "", PlaylistStore.FAVORITES
            )
        )
        playlists_menu.addAction(fav_action)

        media_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        media_menu.addAction(exit_action)

        # Audio menu
        audio_menu = menubar.addMenu("&Audio")

        # Sound Output submenu
        sound_output_menu = audio_menu.addMenu("&Sound Output")

        # Default audio output action
        default_audio_action = QAction("&Default (Auto-adapt)", self)
        default_audio_action.setCheckable(True)
        default_audio_action.setChecked(self.app_state.audio_output_mode == "default")
        default_audio_action.triggered.connect(lambda: self.set_audio_output_mode("default"))
        sound_output_menu.addAction(default_audio_action)

        # Manual audio output action
        manual_audio_action = QAction("&Manual (Choose Device)", self)
        manual_audio_action.setCheckable(True)
        manual_audio_action.setChecked(self.app_state.audio_output_mode == "manual")
        manual_audio_action.triggered.connect(lambda: self.set_audio_output_mode("manual"))
        sound_output_menu.addAction(manual_audio_action)

        # Create audio device submenu for manual mode
        self.audio_device_menu = sound_output_menu.addMenu("&Select Device")
        self.audio_device_menu.setEnabled(self.app_state.audio_output_mode == "manual")
        self.update_audio_device_menu()

        # View menu
        view_menu = menubar.addMenu("&View")

        fullscreen_action = QAction("&Fullscreen", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        expand_action = QAction("&Expand Now Playing", self)
        expand_action.setShortcut("Ctrl+Shift+E")
        expand_action.triggered.connect(self.expand_now_playing_view)
        view_menu.addAction(expand_action)

        minimize_action = QAction("&Minimize Now Playing", self)
        minimize_action.setShortcut("Ctrl+Shift+M")
        minimize_action.triggered.connect(self.minimize_now_playing_view)
        view_menu.addAction(minimize_action)

        now_playing_action = QAction("&Now Playing Panel", self)
        now_playing_action.setShortcut("Ctrl+Shift+N")
        now_playing_action.setCheckable(True)
        now_playing_action.setChecked(True)
        now_playing_action.triggered.connect(lambda: self.toggle_now_playing())
        view_menu.addAction(now_playing_action)

        tray_action = QAction("Minimize to &Tray", self)
        tray_action.setShortcut("Ctrl+Shift+T")
        tray_action.triggered.connect(self.hide_to_tray)
        view_menu.addAction(tray_action)

        clear_queue_action = QAction("Clear &Up Next and Stop", self)
        clear_queue_action.triggered.connect(self.clear_up_next_and_stop)
        view_menu.addAction(clear_queue_action)

        home_action = QAction("&Home", self)
        home_action.setShortcut("Ctrl+H")
        home_action.triggered.connect(lambda: self.show_shell_page("home"))
        view_menu.addAction(home_action)

        # View menu - add media info
        view_menu.addSeparator()

        theme_menu = view_menu.addMenu("&Theme")
        self._theme_action_group = QActionGroup(self)
        self._theme_action_group.setExclusive(True)
        self._theme_actions: Dict[str, QAction] = {}
        for tid, label, _source in list_themes():
            act = QAction(label, self)
            act.setCheckable(True)
            act.setData(tid)
            if tid == self.app_state.theme or (
                self.app_state.theme in ("dark", "light") and tid == "ember"
            ):
                act.setChecked(True)
            act.triggered.connect(lambda checked, t=tid: self._on_theme_chosen(t) if checked else None)
            self._theme_action_group.addAction(act)
            theme_menu.addAction(act)
            self._theme_actions[tid] = act
        theme_menu.addSeparator()
        open_themes_action = QAction("Open Theme Packs &Folder…", self)
        open_themes_action.triggered.connect(self._open_user_themes_folder)
        theme_menu.addAction(open_themes_action)

        view_menu.addSeparator()

        media_info_action = QAction("&Media Info", self)
        media_info_action.setShortcut("Ctrl+I")
        media_info_action.triggered.connect(self.show_media_info)
        view_menu.addAction(media_info_action)

        view_menu.addSeparator()

        refresh_meta_action = QAction("&Refresh Metadata", self)
        refresh_meta_action.setShortcut("Ctrl+Shift+R")
        refresh_meta_action.triggered.connect(self.refresh_current_metadata)
        view_menu.addAction(refresh_meta_action)

        refresh_library_meta_action = QAction("Refresh Metadata for &Library", self)
        refresh_library_meta_action.triggered.connect(self.refresh_library_metadata)
        view_menu.addAction(refresh_library_meta_action)

        # Help menu (with Update options moved here)
        help_menu = menubar.addMenu("&Help")

        help_action = QAction("&Help", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()

        check_updates_action = QAction("&Check for Updates", self)
        check_updates_action.setShortcut("Ctrl+U")
        check_updates_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_updates_action)

        auto_update_action = QAction("Auto-Update &Settings", self)
        auto_update_action.triggered.connect(self.show_update_settings)
        help_menu.addAction(auto_update_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_media_player(self):
        self.current_audio_device = None
        self.volume_amplification = 1.0
        self.base_volume = 1.0

        self.video_widget.show()
        self.video_widget.winId()

        try:
            self.engine = PlaybackEngine(self.video_widget, self)
        except NativeEngineError as exc:
            show_native_engine_failure(str(exc))
            raise

        # Legacy aliases — playback is native C media core only; these stay None.
        self.media_player = None
        self.audio_output = None

        self.engine.position_changed.connect(self.position_changed)
        self.engine.duration_changed.connect(self.duration_changed)
        self.engine.state_changed.connect(self._engine_state_changed)
        self.engine.error_occurred.connect(lambda msg: self.media_error(None, msg))
        self.engine.backend_ready.connect(self._on_backend_ready)

        # 0% is valid — do not use `volume or 100` (truthiness snaps 0 → 100).
        vol = max(0, min(200, int(self.app_state.volume)))
        self.app_state.volume = vol
        self.controls.volume_slider.blockSignals(True)
        self.controls.volume_slider.setValue(vol)
        self.controls.volume_slider.blockSignals(False)
        self.controls.volume_label.setText(f"{vol}%")
        self._apply_output_gain_from_state()
        self._on_backend_ready(self.engine.backend_name)

    def _on_backend_ready(self, name: str):
        if hasattr(self, "engine") and self.engine is not None:
            self.engine.refresh_embed_hint()
        embed = getattr(self.engine, "has_embedded_video", False)
        hint = embed_platform_hint()
        if embed:
            label = "native C core (embedded)"
        elif hint == "wayland-limited":
            label = "native C core (audio; Wayland embed limited)"
        else:
            label = "native C core (audio)"
        if name not in ("native", "mpv"):
            label = "native C core"
        if hasattr(self, "now_playing"):
            self.now_playing.engine_label.setText(f"Engine: {label}")
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage(
                f"Playback engine: {label} — {embed_status_message(hint)}", 6000
            )

    def _reassert_engine_volume(self):
        """Re-push the engine's last logical volume after the native engine opens a stream.

        Uses engine state (not a stale app_state snapshot) so a volume set to 0%
        during the play-start window is not overwritten back to 100%.
        """
        if hasattr(self, "engine") and self.engine is not None:
            self.engine.set_volume_percent(int(self.engine.volume_percent()))

    def _engine_state_changed(self, state: str):
        if state == "playing":
            self.controls.btn_play.setText("⏸")
            if self._preview_timer and not self._preview_timer.isActive():
                self._preview_timer.start()
            # Re-apply volume after stream opens (engine property timing)
            QTimer.singleShot(200, self._reassert_engine_volume)
        else:
            self.controls.btn_play.setText("▶")
            if state == "stopped" and self._preview_timer:
                self._preview_timer.stop()
        self.playback_state_changed(state)
        if hasattr(self, "mpris") and self.mpris is not None:
            self.mpris.notify_properties()

    def setup_shortcuts(self):
        # Space bar for play/pause
        QShortcut(QKeySequence("Space"), self, self.toggle_playback)

        # Arrow keys for seeking
        QShortcut(QKeySequence("Left"), self, lambda: self.seek_relative(-10))
        QShortcut(QKeySequence("Right"), self, lambda: self.seek_relative(10))

        # Previous/Next media navigation
        QShortcut(QKeySequence("P"), self, self.previous_media)
        QShortcut(QKeySequence("N"), self, self.next_media)

        # Volume controls
        QShortcut(QKeySequence("Up"), self, lambda: self.adjust_volume(5))
        QShortcut(QKeySequence("Down"), self, lambda: self.adjust_volume(-5))

        # Mute toggle
        QShortcut(QKeySequence("M"), self, self.toggle_mute)

        # Minimize expanded now-playing / exit fullscreen
        QShortcut(QKeySequence("Esc"), self, self._escape_pressed)

        # Playlist toggle (handled by menu action)

    def _escape_pressed(self):
        if self.isFullScreen():
            self.toggle_fullscreen()
            return
        if self._stage_expanded or self.shell_mode == "stage":
            self.minimize_now_playing_view()

    def setup_timers(self):
        # Timer for updating UI
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(100)  # Update every 100ms

        # Timer for auto-hiding controls
        self.mouse_timer = QTimer()
        self.mouse_timer.timeout.connect(self.hide_controls)
        self.mouse_timer.setSingleShot(True)

        # Timer for auto-hiding playlist in fullscreen
        self.playlist_timer = QTimer()
        self.playlist_timer.timeout.connect(self.hide_playlist)
        self.playlist_timer.setSingleShot(True)

        # Timer for checking audio device changes
        self.audio_device_timer = QTimer()
        self.audio_device_timer.timeout.connect(self.check_audio_device_changes)
        self.audio_device_timer.start(2000)  # Check every 2 seconds

        # Live preview frames for Now Playing / transport while video plays
        self._preview_timer = QTimer()
        self._preview_timer.setInterval(500)
        self._preview_timer.timeout.connect(self._update_live_preview)

    def setup_drag_drop(self):
        """Zone-based drops: library indexes; Now Playing / transport play immediately."""
        self.setAcceptDrops(True)
        if hasattr(self, "video_widget"):
            self.video_widget.setAcceptDrops(True)
        # Home / Now Playing / Transport already accept drops via shell mixins.
        # Do not recursively setAcceptDrops on every child — that breaks zone routing.

    def setup_auto_update(self):
        """Setup auto-update functionality"""
        # Check for updates on startup if enabled
        if self.app_state.auto_update_enabled:
            QTimer.singleShot(5000, self.check_for_updates)  # Check after 5 seconds

    def set_audio_output_mode(self, mode):
        """Set audio output mode (default or manual)"""
        self.app_state.audio_output_mode = mode
        self.settings.settings.setValue("audio_output_mode", mode)

        # Update menu states
        for action in self.menuBar().findChildren(QAction):
            if action.text() == "&Default (Auto-adapt)":
                action.setChecked(mode == "default")
            elif action.text() == "&Manual (Choose Device)":
                action.setChecked(mode == "manual")

        # Enable/disable device selection menu
        if hasattr(self, 'audio_device_menu'):
            self.audio_device_menu.setEnabled(mode == "manual")

        # Update audio device
        self.update_audio_device()

    def update_audio_device_menu(self):
        """Update the audio device selection menu"""
        if not hasattr(self, 'audio_device_menu'):
            return

        # Clear existing actions
        self.audio_device_menu.clear()

        # Simplified approach - just show default device option
        # In a real implementation, you would enumerate available devices
        default_action = QAction("Default Device", self)
        default_action.setCheckable(True)
        default_action.setChecked(True)
        default_action.triggered.connect(lambda: self.select_audio_device("default"))
        self.audio_device_menu.addAction(default_action)

        # Store available devices as empty for now
        self.available_audio_devices = []

    def select_audio_device(self, device_id):
        """Select a specific audio device"""
        self.app_state.selected_audio_device = device_id
        self.settings.settings.setValue("selected_audio_device", device_id)
        self.update_audio_device()

    def update_audio_device(self):
        """Audio device selection is handled by the native engine / OS mixer."""
        self._apply_output_gain_from_state()
        mode = self.app_state.audio_output_mode
        self.status_bar.showMessage(
            f"Audio device: {'Default' if mode == 'default' else 'Manual'} (native / system)",
            2500,
        )

    def show_help(self):
        """Show help dialog"""
        help_text = """
VoxPlayer - Help

Keyboard Shortcuts:
• Space: Play/Pause
• Left/Right Arrow: Seek -10/+10 seconds
• Up/Down Arrow: Volume +5/-5
• M: Mute/Unmute
• F11: Toggle Fullscreen
• Esc: Exit Fullscreen
• Ctrl+O: Open File
• Ctrl+Shift+O: Open Files
• Ctrl+Shift+F: Open Folder
• Ctrl+Shift+N: Toggle Now Playing panel
• Ctrl+I: Import Playlist
• Ctrl+M: Open Magnet Link
• Ctrl+T: Open Torrent File
• Ctrl+E: Export Playlist
• Ctrl+Shift+C: Clear Up next and stop
• Ctrl+U: Check for Updates
• P: Previous Media
• N: Next Media

Features:
• Ultra-compact design for maximum efficiency
• Auto-play next item in playlist
• Audio device detection and selection
• True volume amplification up to 200%
• Advanced drag & drop for multiple files/folders
• Recursive folder scanning for media files
• Torrent streaming support with playlist integration
• Playlist search and filtering
• Previous/Next media buttons and keyboard shortcuts
• Individual playlist item removal with X buttons
• Playlist import/export functionality (M3U, PLS, XSPF)
• Clear playlist option with confirmation
• Smart playlist management (no auto-clearing)
• Auto-update system

For more information, visit the project repository.
        """
        QMessageBox.information(self, "VoxPlayer Help", help_text)

    def show_qbittorrent_webui_setup(self, _checked: bool = False) -> None:
        """Show help copy for enabling the Web UI (no embedded secrets)."""
        QMessageBox.information(
            self,
            "qBittorrent Web UI setup",
            qbittorrent_webui_setup_text(),
        )
        self.settings.settings.setValue("torrent_webui_setup_seen", True)

    def _ensure_torrent_webui_setup_seen(self) -> bool:
        """On first torrent action, show setup guide once. Returns False if user cancels."""
        seen_raw = self.settings.settings.value("torrent_webui_setup_seen", False)
        if isinstance(seen_raw, str):
            seen = seen_raw.strip().lower() in {"1", "true", "yes"}
        else:
            seen = bool(seen_raw)
        if seen:
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Torrent streaming — first run")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(
            "Torrent streaming uses your local qBittorrent Web UI.\n\n"
            "Read the short setup guide before continuing. "
            "VoxPlayer never ships default passwords."
        )
        box.setInformativeText(qbittorrent_webui_setup_text())
        cont = box.addButton("Continue", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not cont:
            return False
        self.settings.settings.setValue("torrent_webui_setup_seen", True)
        return True

    def open_magnet_link(self):
        """Open magnet link dialog"""
        if not self._ensure_torrent_webui_setup_seen():
            return
        magnet_link, ok = QInputDialog.getText(
            self, "Open Magnet Link", "Enter magnet link:"
        )
        if ok and magnet_link:
            self.start_torrent_streaming(magnet_link)

    def open_torrent_file(self):
        """Open torrent file dialog"""
        if not self._ensure_torrent_webui_setup_seen():
            return
        default_dir = os.path.expanduser("~/Downloads/Torrents")
        if not os.path.isdir(default_dir):
            default_dir = os.path.expanduser("~/Downloads")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Torrent File", default_dir, "Torrent Files (*.torrent)"
        )
        if file_path:
            self.start_torrent_streaming(torrent_file=file_path)

    def start_torrent_streaming(self, magnet_link: str = None, torrent_file: str = None):
        """Start torrent streaming (audio/video only; multi-file asks before clearing Up next)."""
        if self.torrent_streamer and (
            self.torrent_streamer.isRunning() or self.torrent_streamer.torrent_hash
        ):
            QMessageBox.warning(self, "Torrent Active", "A torrent is already being streamed.")
            return

        preferred = None
        preferred_list: List[str] = []
        # Gate .torrent files before contacting the client
        if torrent_file:
            ok, msg, paths = validate_torrent_file(torrent_file)
            if not ok:
                QMessageBox.warning(
                    self,
                    "Torrent Rejected",
                    f"{msg}\n\nVoxPlayer only accepts torrents that contain "
                    "audio and/or video files.",
                )
                self.status_bar.showMessage("Torrent rejected: not audio/video media.")
                return
            media = media_paths_only(paths)
            if len(media) > 1:
                confirm = QMessageBox.question(
                    self,
                    "Multi-file torrent",
                    "This torrent contains multiple audio/video files "
                    f"({len(media)}).\n\n"
                    "Your Up next list will be cleared so the torrent file tree "
                    "can be shown. Check any files from any folder (for example "
                    "episodes across seasons), then confirm.\n\nContinue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if confirm != QMessageBox.StandardButton.Yes:
                    return
                self.clear_up_next_and_stop()
                picker = TorrentFilePickerDialog(
                    media, self, title="Choose files to stream"
                )
                if picker.exec() != QDialog.DialogCode.Accepted:
                    return
                preferred_list = picker.selected_paths()
                if not preferred_list:
                    return
                preferred = preferred_list[0]
            elif len(media) == 1:
                preferred = media[0]
                preferred_list = [preferred]

        self._stop_torrent_session(silent=True)
        self.torrent_streamer = TorrentStreamer(
            magnet_link=magnet_link,
            torrent_file=torrent_file,
            preferred_relative_path=preferred,
            preferred_relative_paths=preferred_list if torrent_file else None,
        )
        self._pending_torrent_rel_paths = list(preferred_list) if torrent_file else []
        self.torrent_streamer.progress_updated.connect(self.on_torrent_progress)
        self.torrent_streamer.file_ready.connect(self.on_torrent_file_ready)
        self.torrent_streamer.error_occurred.connect(self.on_torrent_error)
        self.torrent_streamer.start()

        if magnet_link:
            self.status_bar.showMessage("Starting magnet link stream...")
        elif torrent_file:
            self.status_bar.showMessage("Starting torrent file stream...")

    def _stop_torrent_session(self, silent: bool = False):
        """Delete active torrent transfer from the client (no further up/down)."""
        if not self.torrent_streamer:
            if not silent:
                QMessageBox.information(self, "No Torrent", "No torrent is currently active.")
            return
        try:
            self.torrent_streamer.stop()
            if self.torrent_streamer.isRunning():
                self.torrent_streamer.wait(8000)
        except Exception:
            pass
        self.torrent_streamer = None
        self._torrent_active_paths = set()
        if not silent:
            self.status_bar.showMessage("Torrent stopped.")

    def _maybe_release_torrent_after_queue_change(self):
        """If no torrent paths remain in Up next, stop the transfer entirely."""
        if not self._torrent_active_paths:
            return
        queued = set()
        if hasattr(self, "playlist"):
            for i in range(self.playlist.count()):
                p = self.playlist.get_file_at_index(i)
                if p:
                    queued.add(os.path.abspath(p))
        remaining = {os.path.abspath(p) for p in self._torrent_active_paths} & queued
        playing = os.path.abspath(self.app_state.last_file) if self.app_state.last_file else ""
        if playing in self._torrent_active_paths:
            remaining.add(playing)
        if not remaining:
            self._stop_torrent_session(silent=True)
            self.status_bar.showMessage("Torrent removed — transfer stopped.", 4000)

    def stop_torrent(self):
        """Stop torrent streaming"""
        if self.torrent_streamer:
            self._stop_torrent_session(silent=False)
        else:
            QMessageBox.information(self, "No Torrent", "No torrent is currently active.")

    def on_torrent_progress(self, progress: int, status: str):
        """Handle torrent progress updates"""
        self.status_bar.showMessage(f"Torrent: {status} ({progress}%)")

    def on_torrent_file_ready(self, file_path: str):
        """Handle torrent file ready"""
        abs_path = os.path.abspath(file_path)
        self._torrent_active_paths.add(abs_path)
        # Add to playlist first
        self.playlist.add_media_file(file_path)
        # Queue other user-selected torrent files once their paths resolve on disk.
        self._queue_other_selected_torrent_files(abs_path)
        self.playlist.setCurrentRow(self.playlist.find_file_index(file_path) or 0)

        # Load and play the media
        self.load_media(file_path)
        if self.torrent_streamer:
            self.torrent_streamer.resume_transfer()
        QTimer.singleShot(100, self._engine_play)

        self.status_bar.showMessage(f"Torrent file ready: {os.path.basename(file_path)}")

    def _queue_other_selected_torrent_files(self, first_abs: str) -> None:
        """Add other checked torrent relatives into Up next when present on disk."""
        rels = list(getattr(self, "_pending_torrent_rel_paths", []) or [])
        if len(rels) <= 1:
            return
        first_rel = rels[0].replace("\\", "/")
        # Infer content root from the first ready file path.
        norm_first = first_abs.replace("\\", "/")
        root = None
        idx = norm_first.lower().find(first_rel.lower())
        if idx >= 0:
            root = norm_first[:idx]
        if not root:
            root = os.path.dirname(first_abs) + os.sep
        for rel in rels[1:]:
            cand = os.path.normpath(os.path.join(root, rel.replace("/", os.sep)))
            if os.path.isfile(cand):
                self._torrent_active_paths.add(os.path.abspath(cand))
                if self.playlist.find_file_index(cand) is None:
                    self.playlist.add_media_file(cand)
        self._sync_now_playing_queue()

    def on_torrent_error(self, error_message: str):
        """Handle torrent errors"""
        QMessageBox.warning(self, "Torrent Error", error_message)
        self.status_bar.showMessage("Torrent error occurred.")
        self._stop_torrent_session(silent=True)

    def filter_playlist(self, search_text):
        """Filter playlist items based on search text"""
        if not hasattr(self, 'playlist'):
            return

        search_text = search_text.lower().strip()

        for i in range(self.playlist.count()):
            item = self.playlist.item(i)
            if item:
                # Get the custom widget for this item
                item_widget = self.playlist.itemWidget(item)
                if item_widget:
                    # Find the label widget within the custom widget
                    label_widget = item_widget.findChild(QLabel)
                    if label_widget:
                        item_text = label_widget.text().lower()
                        if search_text in item_text:
                            item.setHidden(False)
                        else:
                            item.setHidden(True)
                    else:
                        # Fallback to item text if no label found
                        item_text = item.text().lower()
                        if search_text in item_text:
                            item.setHidden(False)
                        else:
                            item.setHidden(True)
                else:
                    # Fallback to item text if no custom widget
                    item_text = item.text().lower()
                    if search_text in item_text:
                        item.setHidden(False)
                    else:
                        item.setHidden(True)

        # Update clear button visibility
        if hasattr(self, 'clear_search_btn'):
            self.clear_search_btn.setVisible(bool(search_text))

    def clear_playlist_search(self):
        """Clear the playlist search"""
        if hasattr(self, 'playlist_search'):
            self.playlist_search.clear()

    def import_playlist(self):
        """Import playlist from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Playlist", "", "Playlist Files (*.m3u *.m3u8 *.pls *.xspf);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Don't clear current playlist - add to existing items

                # Parse different playlist formats
                if file_path.endswith('.m3u') or file_path.endswith('.m3u8'):
                    self._import_m3u_playlist(content)
                elif file_path.endswith('.pls'):
                    self._import_pls_playlist(content)
                elif file_path.endswith('.xspf'):
                    self._import_xspf_playlist(content)
                else:
                    # Try to parse as simple text file with one file per line
                    self._import_text_playlist(content)

                self.status_bar.showMessage(f"Playlist imported: {os.path.basename(file_path)}")

            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Failed to import playlist:\n{str(e)}")

    def export_playlist(self):
        """Export playlist to file"""
        if not hasattr(self, 'playlist') or self.playlist.count() == 0:
            QMessageBox.information(self, "Export Playlist", "Playlist is empty. Nothing to export.")
            return

        # Get filename from user
        filename, _ = QInputDialog.getText(
            self, "Export Playlist", "Enter playlist filename (without extension):",
            text="VoxPlayer_Playlist"
        )

        if not filename:
            return

        # Add .m3u extension if not provided
        if not filename.endswith('.m3u'):
            filename += '.m3u'

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Playlist", filename, "M3U Playlist (*.m3u);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("#EXTM3U\n")
                    for i in range(self.playlist.count()):
                        item = self.playlist.item(i)
                        if item:
                            file_path_item = item.data(Qt.ItemDataRole.UserRole)
                            f.write(f"{file_path_item}\n")

                self.status_bar.showMessage(f"Playlist exported: {os.path.basename(file_path)}")

            except Exception as e:
                QMessageBox.warning(self, "Export Error", f"Failed to export playlist:\n{str(e)}")

    def _import_m3u_playlist(self, content):
        """Import M3U playlist format"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                if os.path.exists(line):
                    self.playlist.add_media_file(line)

    def _import_pls_playlist(self, content):
        """Import PLS playlist format"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('File'):
                file_path = line.split('=', 1)[1].strip()
                if os.path.exists(file_path):
                    self.playlist.add_media_file(file_path)

    def _import_xspf_playlist(self, content):
        """Import XSPF playlist format (basic implementation)"""
        # This is a basic implementation - for full XSPF support, use xml parsing
        lines = content.split('\n')
        for line in lines:
            if '<location>' in line:
                file_path = line.split('<location>')[1].split('</location>')[0].strip()
                if os.path.exists(file_path):
                    self.playlist.add_media_file(file_path)

    def _import_text_playlist(self, content):
        """Import simple text playlist (one file per line)"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and os.path.exists(line):
                self.playlist.add_media_file(line)

    def clear_playlist(self):
        """Clear all items from the playlist"""
        if not hasattr(self, 'playlist'):
            return

        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Clear Playlist",
            "Are you sure you want to clear the entire playlist?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Stop current playback if playing
            if hasattr(self, "engine") and self.engine is not None:
                self.engine.stop()

            # Clear the playlist
            self.playlist.clear()

            self.app_state.last_file = ""
            self.setWindowTitle("VoxPlayer")
            self._sync_now_playing_queue()
            if hasattr(self, "now_playing"):
                self.now_playing.update_now_playing(None)
            if hasattr(self, "controls"):
                self.controls.set_track_meta("VoxPlayer", "Ready")
                self.controls.set_track_art()
                self.controls.update_time(0, 0)
                self.controls.update_seek_position(0)
            self.status_bar.showMessage("Playlist cleared")

    def check_for_updates(self):
        """Check for updates"""
        if self.update_checker and self.update_checker.isRunning():
            return

        self.update_checker = UpdateChecker(self.current_version)
        self.update_checker.update_available.connect(self.on_update_available)
        self.update_checker.check_completed.connect(self.on_update_check_completed)
        self.update_checker.start()

        self.status_bar.showMessage("Checking for updates...")

    def on_update_available(self, update_info: dict):
        """Handle update available"""
        reply = QMessageBox.question(
            self, "Update Available",
            f"Version {update_info['version']} is available!\n\n"
            f"Release Notes:\n{update_info['release_notes'][:200]}...\n\n"
            "Would you like to download it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            webbrowser.open(update_info['download_url'])
            self.status_bar.showMessage("Opening download page...")

    def on_update_check_completed(self, has_update: bool):
        """Handle update check completed"""
        if not has_update:
            self.status_bar.showMessage("You have the latest version.")

    def show_update_settings(self):
        """Show update settings dialog"""
        QMessageBox.information(
            self, "Update Settings",
            "Auto-update is currently enabled.\n"
            "Updates are checked on startup and can be checked manually.\n"
            "Settings will be configurable in future versions."
        )

    def check_audio_device_changes(self):
        """native engine owns the audio device; re-assert volume if a stream is active."""
        try:
            if hasattr(self, "engine") and self.engine is not None and self.engine.is_playing():
                self._apply_output_gain_from_state()
        except Exception:
            pass

    def dragEnterEvent(self, event):
        """Handle drag enter events (window chrome / stage fallback → play)."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if self.is_supported_media_file(file_path) or os.path.isdir(file_path):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        """Window-level drop (stage / chrome) → play immediately."""
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile()]
            if paths:
                self.handle_shell_drop(paths, "play")
                event.acceptProposedAction()
                return
        event.ignore()

    def _collect_dropped_media(self, paths: List[str]) -> List[str]:
        """Expand folders and filter to supported audio/video paths."""
        media_files: List[str] = []
        for file_path in paths:
            if not file_path:
                continue
            if os.path.isdir(file_path):
                folder_media = self.find_media_files_in_folder(file_path)
                media_files.extend(folder_media)
                if folder_media:
                    self.status_bar.showMessage(
                        f"Scanning folder: {os.path.basename(file_path)} ({len(folder_media)} files)",
                        2000,
                    )
            elif self.is_supported_media_file(file_path):
                media_files.append(file_path)
        seen = set()
        unique: List[str] = []
        for p in media_files:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        return unique

    def handle_shell_drop(self, paths: list, mode: str = "play"):
        """
        Zone-aware drop handler.

        - mode ``index``: add to library only (no autoplay) — Home / library grid
        - mode ``play``: add to Up next and play immediately — Now Playing / transport
        """
        unique = self._collect_dropped_media(list(paths or []))
        if not unique:
            self._warn_unsupported_paths(list(paths or []), context="drop")
            return

        if mode == "index":
            for file_path in unique:
                self._register_library_path(file_path)
            self.refresh_home_grid()
            self.status_bar.showMessage(
                f"Indexed {len(unique)} item{'s' if len(unique) != 1 else ''} into library",
                4000,
            )
            return

        # Play immediately
        for file_path in unique:
            self._register_library_path(file_path)
            if file_path not in [
                self.playlist.get_file_at_index(i) for i in range(self.playlist.count())
            ]:
                self.playlist.add_media_file(file_path)
        self.load_media(unique[0])
        self.playlist.setCurrentRow(0)
        QTimer.singleShot(100, self._engine_play)
        self._sync_now_playing_queue()
        self.toggle_now_playing(True)
        self.refresh_home_grid()
        self.status_bar.showMessage(
            f"Playing {os.path.basename(unique[0])} (+{len(unique) - 1} queued)"
            if len(unique) > 1
            else f"Playing {os.path.basename(unique[0])}",
            4000,
        )

    def _engine_play(self):
        if self.torrent_streamer and self.app_state.last_file:
            abs_last = os.path.abspath(self.app_state.last_file)
            if abs_last in self._torrent_active_paths:
                self.torrent_streamer.resume_transfer()
        if hasattr(self, "engine") and self.engine is not None:
            self.engine.play()

    def find_media_files_in_folder(self, folder_path):
        """Find all supported media files in a folder recursively (native scan when built)."""
        video_formats = [
            ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp", ".3g2", ".mj2",
            ".mpg", ".mpeg", ".ts", ".m2ts",
        ]
        audio_formats = [
            ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus", ".ape", ".aiff",
        ]
        exts = video_formats + audio_formats
        native = scan_media_dir(folder_path, exts)
        if native is not None:
            return native
        media_files = []
        try:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.is_supported_media_file(file_path):
                        media_files.append(file_path)
        except (PermissionError, OSError) as e:
            self.status_bar.showMessage(f"Error accessing folder: {e}", 3000)
        return media_files

    def is_supported_media_file(self, file_path):
        """Check if file is a supported media format"""
        if not file_path or not os.path.exists(file_path):
            return False

        # Get file extension
        _, ext = os.path.splitext(file_path.lower())

        # Supported video formats
        video_formats = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.3g2', '.mj2', '.mpg', '.mpeg']

        # Supported audio formats
        audio_formats = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus']

        return ext in video_formats or ext in audio_formats

    def exit_fullscreen(self):
        """Exit fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
            self.controls.show()
            self.controls_visible = True
            self.mouse_timer.stop()

    def apply_theme(self):
        """Apply selected palette into COLORS and refresh the shell stylesheet."""
        tid = apply_theme_id(getattr(self.app_state, "theme", None) or "ember")
        self.app_state.theme = tid
        self.setStyleSheet(app_stylesheet())
        if hasattr(self, "_theme_actions"):
            act = self._theme_actions.get(tid)
            if act is not None:
                act.setChecked(True)

    def _on_theme_chosen(self, theme_id: str) -> None:
        self.app_state.theme = theme_id
        self.apply_theme()
        self.settings.save_state(self.app_state)
        if hasattr(self, "home_view"):
            self.refresh_home_grid()
        label = theme_id
        for tid, name, _src in list_themes():
            if tid == theme_id:
                label = name
                break
        self.status_bar.showMessage(f"Theme: {label}", 3000)

    def _open_user_themes_folder(self) -> None:
        path = user_themes_dir()
        try:
            webbrowser.open(QUrl.fromLocalFile(path).toString())
        except Exception:
            QMessageBox.information(
                self,
                "Theme Packs",
                f"Place JSON theme packs in:\n{path}\n\n"
                "Each file needs a colors object with keys like accent, bg_app, text.",
            )

    def _supported_formats_hint(self) -> str:
        return (
            "Supported formats: MP4, MKV, WebM, AVI, MOV, MP3, FLAC, M4A, Opus, OGG, WAV, and similar.\n"
            "Archives, disk images, executables, and documents are not playable."
        )

    def _warn_unsupported_paths(self, paths: List[str], context: str = "open") -> None:
        """Surface a clear message when nothing in the selection is playable."""
        samples: List[str] = []
        for p in paths:
            if not p:
                continue
            if os.path.isdir(p):
                samples.append(f"{os.path.basename(p)}/ (folder — no media found)")
            else:
                ext = os.path.splitext(p)[1].lower() or "(no extension)"
                samples.append(f"{os.path.basename(p)} ({ext})")
            if len(samples) >= 5:
                break
        detail = "\n".join(f"• {s}" for s in samples) if samples else "• (empty selection)"
        verb = {
            "drop": "Nothing playable was in that drop.",
            "open": "That selection is not a supported media format.",
            "folder": "No supported media files were found in that folder.",
        }.get(context, "No supported media found.")
        QMessageBox.information(
            self,
            "Unsupported format",
            f"{verb}\n\n{detail}\n\n{self._supported_formats_hint()}",
        )
        self.status_bar.showMessage("Unsupported format — see dialog for details", 5000)

    def setup_icon(self):
        """Setup application and window icons"""
        try:
            # Try to load icon from package directory first
            icon_path = os.path.join(os.path.dirname(__file__), "logo.png")
            if not os.path.exists(icon_path):
                # Fallback to current directory
                icon_path = "logo.png"
            if os.path.exists(icon_path):
                # Set window icon
                self.setWindowIcon(QIcon(icon_path))

                # Create a pixmap for the video widget background
                self.logo_pixmap = QPixmap(icon_path)
                if not self.logo_pixmap.isNull():
                    # Scale the logo to fit nicely in the video widget
                    self.logo_pixmap = self.logo_pixmap.scaled(
                        200, 200, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    # Set the video widget background
                    self.setup_video_widget_background()
        except Exception as e:
            print(f"Warning: Could not load application icon: {e}")

    def setup_video_widget_background(self):
        """Setup video widget background with logo"""
        if hasattr(self, 'logo_pixmap') and not self.logo_pixmap.isNull():
            # Create a logo label overlay for the video widget
            self.logo_label = QLabel(self.video_widget)
            self.logo_label.setPixmap(self.logo_pixmap)
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.logo_label.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)
            self.logo_label.show()
            self.logo_label.raise_()

            # Position the logo in the center of the video widget
            self.position_logo()

    def position_logo(self):
        """Position the logo in the center of the video widget"""
        if hasattr(self, 'logo_label') and self.logo_label:
            video_rect = self.video_widget.rect()
            logo_rect = self.logo_label.rect()

            # Center the logo
            x = (video_rect.width() - logo_rect.width()) // 2
            y = (video_rect.height() - logo_rect.height()) // 2

            self.logo_label.move(x, y)

    def show_logo(self, show=True):
        """Show or hide the logo in the video widget"""
        if hasattr(self, 'logo_label') and self.logo_label:
            self.logo_label.setVisible(show)

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        # Reposition logo when window is resized
        self.position_logo()

    def open_file(self):
        """Open file dialog and load media"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Media File", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v);;"
            "Audio Files (*.mp3 *.flac *.wav *.ogg *.m4a *.aac *.wma *.opus);;"
            "All Files (*)"
        )

        if file_path:
            if not self.is_supported_media_file(file_path):
                self._warn_unsupported_paths([file_path], context="open")
                return
            self.load_media(file_path)
            self.playlist.add_media_file(file_path)
            self.playlist.setCurrentRow(self.playlist.count() - 1)
            self._register_library_path(file_path)
            self.refresh_home_grid()

    def open_files(self):
        """Open multiple files dialog and load media"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Media Files", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v);;"
            "Audio Files (*.mp3 *.flac *.wav *.ogg *.m4a *.aac *.wma *.opus);;"
            "All Files (*)"
        )

        if file_paths:
            supported = [p for p in file_paths if self.is_supported_media_file(p)]
            skipped = [p for p in file_paths if p not in supported]
            if not supported:
                self._warn_unsupported_paths(file_paths, context="open")
                return
            if skipped:
                self.status_bar.showMessage(
                    f"Skipped {len(skipped)} unsupported file(s)", 4000
                )
            for file_path in supported:
                self.playlist.add_media_file(file_path)
                self._register_library_path(file_path)
            self.load_media(supported[0])
            self.playlist.setCurrentRow(0)
            self.refresh_home_grid()

    def open_folder(self):
        """Open folder dialog, index media, and persist the root for next launch."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Open Media Folder", ""
        )

        if folder_path:
            media_files = self.find_media_files_in_folder(folder_path)
            if media_files:
                media_files.sort()
                self._remember_library_root(folder_path)
                for file_path in media_files:
                    self.playlist.add_media_file(file_path)
                    self._register_library_path(file_path)
                self._rebuild_shuffle_order()
                self.load_media(media_files[0])
                self.playlist.setCurrentRow(0)
                self.refresh_home_grid()
                self.status_bar.showMessage(
                    f"Indexed {len(media_files)} files from {folder_path}", 4000
                )
            else:
                self._warn_unsupported_paths([folder_path], context="folder")

    def load_media(self, file_path):
        """Load media file into player"""
        try:
            # Convert string path to QUrl
            if file_path.startswith(('http://', 'https://', 'ftp://')):
                url = QUrl(file_path)
            else:
                # Ensure the file exists for local files
                if not os.path.exists(file_path):
                    QMessageBox.warning(self, "File Error", f"File not found: {file_path}")
                    return
                if not self.is_supported_media_file(file_path):
                    self._warn_unsupported_paths([file_path], context="open")
                    return
                url = QUrl.fromLocalFile(file_path)

            if hasattr(self, "engine"):
                self.engine.set_source(file_path)
            self._last_media_error_body = None
            self.app_state.last_file = file_path
            self._register_library_path(file_path)
            if file_path not in [self.playlist.get_file_at_index(i) for i in range(self.playlist.count())]:
                self.playlist.add_media_file(file_path)
            self.refresh_home_grid()

            self.show_logo(False)
            # Audio keeps the library visible; video expands the stage automatically.
            if self.is_video_path(file_path):
                self.show_shell_page("stage")
                if hasattr(self, "engine") and self.engine is not None:
                    # Soft rebind first (no stop); hard only if soft fails after stage show.
                    def _rebind(hard: bool = False):
                        self.video_widget.show()
                        self.video_widget.winId()
                        rebound = self.engine.rebind_video_widget(hard=hard)
                        if hasattr(self, "now_playing"):
                            label = (
                                "native C core (embedded)"
                                if rebound or self.engine.has_embedded_video
                                else "native C core (audio)"
                            )
                            self.now_playing.engine_label.setText(f"Engine: {label}")
                        if rebound or self.engine.has_embedded_video:
                            self.engine.play()
                        else:
                            hint = embed_platform_hint()
                            self.status_bar.showMessage(
                                f"Video embed limited ({hint}) — audio via native engine still works",
                                5000,
                            )

                    QTimer.singleShot(50, lambda: _rebind(False))
                    QTimer.singleShot(250, lambda: _rebind(True))
            else:
                self.minimize_now_playing_view()

            if hasattr(self, 'playlist') and self.playlist:
                current_index = self.playlist.find_file_index(file_path)
                if current_index is not None:
                    self.playlist.setCurrentRow(current_index)

            filename = os.path.basename(file_path)
            self.setWindowTitle(f"{filename} - VoxPlayer")

            thumb = self.thumb_cache.ensure(file_path)
            if thumb:
                self._thumb_map[file_path] = thumb

            if hasattr(self, "now_playing"):
                embed = getattr(self.engine, "has_embedded_video", False) if hasattr(self, "engine") else False
                label = "native C core (embedded)" if embed else "native C core (audio)"
                self.now_playing.update_now_playing(
                    file_path, label, thumbnail_path=thumb
                )
                queue_paths = [self.playlist.get_file_at_index(i) for i in range(self.playlist.count())]
                self.now_playing.set_queue([p for p in queue_paths if p], file_path)
            if hasattr(self, "controls"):
                self.controls.set_track_meta(filename, os.path.dirname(file_path))
                if thumb:
                    self.controls.set_track_art(thumb)

            # Get file info for status display
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            file_size_mb = file_size / (1024 * 1024)
            file_ext = os.path.splitext(file_path)[1].upper()

            self.status_bar.showMessage(f"Loaded: {filename} ({file_size_mb:.1f}MB, {file_ext})")

            # Sidecar subtitles: SRT / WebVTT / ASS / SSA
            if hasattr(self, "subtitle_manager"):
                self.subtitle_manager.clear()
            subs = companion_subtitle_paths(file_path)
            if subs and hasattr(self, "subtitle_manager"):
                if self.subtitle_manager.load_subtitles(subs[0]):
                    self.status_bar.showMessage(
                        f"Loaded: {filename} + {os.path.basename(subs[0])} "
                        f"({file_size_mb:.1f}MB, {file_ext})",
                        4000,
                    )

            # Local tags immediately; network only if online and not yet cached
            try:
                local_meta = load_local_metadata(file_path)
                self._meta_cache[file_path] = local_meta
                self._apply_enriched_metadata(local_meta, quiet=True)
            except Exception:
                pass
            QTimer.singleShot(
                50, lambda p=file_path: self._enrich_current_media(p, force_refresh=False)
            )

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load media file:\n{str(e)}")
            self.status_bar.showMessage(f"Error loading: {os.path.basename(file_path)}")

    def _enrich_current_media(self, file_path: str, force_refresh: bool = False):
        """Async enrichment: cache hit / offline = local only; online fetch once."""
        if not file_path or not os.path.isfile(file_path):
            return

        # In-memory hit with completed network (unless user refresh)
        existing = self._meta_cache.get(file_path)
        if existing and existing.network_attempted and not force_refresh:
            self._apply_enriched_metadata(existing, quiet=True)
            return

        cover_dest = self.thumb_cache.path_for(file_path + ".cover")
        # Skip starting network work when clearly offline (still apply disk cache via enrich)
        allow_network = True
        if not force_refresh:
            try:
                allow_network = is_online()
            except Exception:
                allow_network = False

        worker = MetadataEnrichWorker(
            file_path,
            cover_dest,
            self,
            force_refresh=force_refresh,
            allow_network=allow_network or force_refresh,
        )
        self._enrich_thread = worker

        def _on_done(meta: MediaMetadata):
            if not meta:
                return
            self._meta_cache[meta.path] = meta
            if meta.path != getattr(self.app_state, "last_file", ""):
                return
            self._apply_enriched_metadata(meta, quiet=not force_refresh)

        worker.finished_meta.connect(_on_done)
        worker.start()

    def refresh_current_metadata(self):
        """User-requested re-fetch for the current file (online only)."""
        path = getattr(self.app_state, "last_file", "") or ""
        if not path or not os.path.isfile(path):
            self.status_bar.showMessage("No media loaded to refresh metadata.", 3000)
            return
        if not is_online(force=True):
            self.status_bar.showMessage(
                "Offline — using local tags only. Connect to refresh online metadata.",
                4000,
            )
            local = load_local_metadata(path)
            self._meta_cache[path] = local
            self._apply_enriched_metadata(local, quiet=False)
            return
        self.status_bar.showMessage("Refreshing metadata…", 2000)
        self._enrich_current_media(path, force_refresh=True)

    def refresh_library_metadata(self):
        """User-requested refresh for library paths (sequential background workers)."""
        paths = list(getattr(self, "library_paths", []) or [])
        if hasattr(self, "playlist"):
            for i in range(self.playlist.count()):
                p = self.playlist.get_file_at_index(i)
                if p and p not in paths:
                    paths.append(p)
        paths = [p for p in paths if p and os.path.isfile(p)]
        if not paths:
            self.status_bar.showMessage("Library is empty.", 3000)
            return
        if not is_online(force=True):
            self.status_bar.showMessage(
                f"Offline — kept local tags for {len(paths)} items (no network refresh).",
                4000,
            )
            return

        self._library_refresh_queue = list(paths)
        self.status_bar.showMessage(
            f"Refreshing metadata for {len(paths)} library items…", 4000
        )
        self._pump_library_metadata_refresh()

    def _pump_library_metadata_refresh(self):
        queue = getattr(self, "_library_refresh_queue", None) or []
        if not queue:
            self.status_bar.showMessage("Library metadata refresh complete.", 4000)
            self.refresh_home_grid()
            return
        path = queue.pop(0)
        self._library_refresh_queue = queue
        cover_dest = self.thumb_cache.path_for(path + ".cover")
        worker = MetadataEnrichWorker(
            path, cover_dest, self, force_refresh=True, allow_network=True
        )

        def _on_done(meta: MediaMetadata):
            if meta and meta.path:
                self._meta_cache[meta.path] = meta
                if meta.cover_path:
                    self._thumb_map[meta.path] = meta.cover_path
                if meta.path == getattr(self.app_state, "last_file", ""):
                    self._apply_enriched_metadata(meta, quiet=True)
            remaining = len(getattr(self, "_library_refresh_queue", []) or [])
            self.status_bar.showMessage(
                f"Library metadata: {remaining} remaining…", 1500
            )
            QTimer.singleShot(200, self._pump_library_metadata_refresh)

        worker.finished_meta.connect(_on_done)
        self._enrich_thread = worker
        worker.start()

    def _apply_enriched_metadata(self, meta: MediaMetadata, quiet: bool = False):
        if not meta:
            return
        title = meta.display_title()
        subtitle = meta.display_subtitle()
        cover = meta.cover_path or self._thumb_map.get(meta.path) or get_thumbnail_path(meta.path)
        if cover:
            self._thumb_map[meta.path] = cover
        if hasattr(self, "now_playing"):
            embed = getattr(self.engine, "has_embedded_video", False) if hasattr(self, "engine") else False
            label = "native C core (embedded)" if embed else "native C core (audio)"
            self.now_playing.update_now_playing(
                meta.path,
                label,
                title=title,
                subtitle=subtitle or meta.source,
                thumbnail_path=cover,
            )
        if hasattr(self, "controls"):
            self.controls.set_track_meta(title, subtitle or os.path.dirname(meta.path))
            if cover:
                self.controls.set_track_art(cover)
        self.setWindowTitle(f"{title} - VoxPlayer")
        if not quiet:
            self.status_bar.showMessage(
                f"Metadata ({meta.source}): {title}"
                + (f" — {subtitle}" if subtitle else ""),
                4000,
            )
            self.refresh_home_grid()

    def _update_live_preview(self):
        """Grab the current video surface into Now Playing + transport art."""
        if not hasattr(self, "video_widget") or not self.app_state.last_file:
            return
        ext = os.path.splitext(self.app_state.last_file)[1].lower()
        video_ext = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
        if ext not in video_ext:
            return
        playing = False
        if hasattr(self, "engine"):
            playing = self.engine.is_playing()
        if not playing:
            return
        try:
            pix = self.video_widget.grab()
            if pix is None or pix.isNull():
                return
            if hasattr(self, "now_playing"):
                self.now_playing.set_art_pixmap(pixmap=pix)
            if hasattr(self, "controls"):
                self.controls.set_track_art(pixmap=pix)
        except Exception:
            pass

    def load_and_play_media(self, file_path):
        """Load media file and auto-play it"""
        self.load_media(file_path)
        if file_path and hasattr(self, "library_index"):
            self.library_index.record_play(file_path)
            self.library_index.save()
            if getattr(self, "_shell_page", "") in ("home", "browse", "library"):
                self.refresh_facets()
        if hasattr(self, "engine") and self.app_state.last_file:
            QTimer.singleShot(200, self._start_playback_with_gain)

    def _start_playback_with_gain(self):
        """Start playback then re-apply engine volume after the stream opens."""
        if hasattr(self, "engine") and self.engine is not None:
            self.engine.play()
        QTimer.singleShot(400, self._reassert_engine_volume)
        QTimer.singleShot(1200, self._reassert_engine_volume)
        if self._preview_timer and not self._preview_timer.isActive():
            self._preview_timer.start()

    def _playlist_paths(self) -> List[str]:
        if not hasattr(self, "playlist") or self.playlist is None:
            return []
        return [
            p
            for i in range(self.playlist.count())
            for p in [self.playlist.get_file_at_index(i)]
            if p
        ]

    def _rebuild_shuffle_order(self, prefer_current: bool = True) -> None:
        n = self.playlist.count() if hasattr(self, "playlist") and self.playlist else 0
        order = list(range(n))
        random.shuffle(order)
        self._shuffle_order = order
        self._shuffle_pos = 0
        if prefer_current and self.app_state.last_file:
            cur = self.playlist.find_file_index(self.app_state.last_file)
            if cur is not None and cur in self._shuffle_order:
                self._shuffle_pos = self._shuffle_order.index(cur)

    def _queue_index_for_step(self, delta: int) -> Optional[int]:
        """Resolve next/prev playlist index honoring shuffle + repeat."""
        if not hasattr(self, "playlist") or self.playlist is None or self.playlist.count() == 0:
            return None
        n = self.playlist.count()
        current = (
            self.playlist.find_file_index(self.app_state.last_file)
            if self.app_state.last_file
            else None
        )
        if self.app_state.shuffle_enabled:
            if len(self._shuffle_order) != n:
                self._rebuild_shuffle_order()
            if not self._shuffle_order:
                return None
            if current is not None and current in self._shuffle_order:
                self._shuffle_pos = self._shuffle_order.index(current)
            nxt = self._shuffle_pos + delta
            if 0 <= nxt < len(self._shuffle_order):
                self._shuffle_pos = nxt
                return self._shuffle_order[nxt]
            if self.app_state.repeat_mode == "all":
                self._rebuild_shuffle_order(prefer_current=False)
                self._shuffle_pos = 0 if delta > 0 else len(self._shuffle_order) - 1
                return self._shuffle_order[self._shuffle_pos]
            return None
        if current is None:
            return 0 if delta > 0 else n - 1
        nxt = current + delta
        if 0 <= nxt < n:
            return nxt
        if self.app_state.repeat_mode == "all":
            return 0 if delta > 0 else n - 1
        return None

    def _play_queue_index(self, index: int, status_prefix: str = "") -> bool:
        path = self.playlist.get_file_at_index(index)
        if not path:
            return False
        self.playlist.setCurrentRow(index)
        self.load_media(path)
        QTimer.singleShot(100, self._engine_play)
        label = os.path.basename(path)
        self.status_bar.showMessage(
            f"{status_prefix}{label}" if status_prefix else label, 3000
        )
        return True

    def previous_media(self):
        """Go to previous media in Up next (shuffle / wrap when enabled)."""
        idx = self._queue_index_for_step(-1)
        if idx is None:
            self.status_bar.showMessage("No previous track", 2500)
            return
        self._play_queue_index(idx, "Previous: ")

    def next_media(self):
        """Go to next media in Up next (shuffle / wrap when enabled)."""
        idx = self._queue_index_for_step(1)
        if idx is None:
            self.status_bar.showMessage("No next track", 2500)
            return
        self._play_queue_index(idx, "Next: ")

    def toggle_shuffle(self):
        self.app_state.shuffle_enabled = not bool(self.app_state.shuffle_enabled)
        if self.app_state.shuffle_enabled:
            self._rebuild_shuffle_order()
        self.settings.save_state(self.app_state)
        if hasattr(self, "controls"):
            self.controls.sync_playback_modes(
                self.app_state.shuffle_enabled, self.app_state.repeat_mode
            )
        self.status_bar.showMessage(
            "Shuffle on" if self.app_state.shuffle_enabled else "Shuffle off", 2500
        )

    def cycle_repeat_mode(self):
        order = ("off", "all", "one")
        cur = self.app_state.repeat_mode if self.app_state.repeat_mode in order else "off"
        self.app_state.repeat_mode = order[(order.index(cur) + 1) % len(order)]
        self.settings.save_state(self.app_state)
        if hasattr(self, "controls"):
            self.controls.sync_playback_modes(
                self.app_state.shuffle_enabled, self.app_state.repeat_mode
            )
        labels = {"off": "Repeat off", "all": "Repeat all", "one": "Repeat one"}
        self.status_bar.showMessage(labels[self.app_state.repeat_mode], 2500)

    def play_selected_item(self):
        """Play the currently selected playlist item"""
        file_path = self.playlist.get_current_file()
        if file_path:
            self.load_media(file_path)
            self.toggle_playback()

    def toggle_playback(self):
        """Toggle play/pause"""
        if not hasattr(self, "engine") or self.engine is None:
            return
        if self.engine.is_playing():
            self.engine.pause()
            if self.torrent_streamer and self.app_state.last_file:
                if os.path.abspath(self.app_state.last_file) in self._torrent_active_paths:
                    self.torrent_streamer.pause_transfer()
                    self.status_bar.showMessage("Torrent transfer paused (not playing).", 3000)
        else:
            self._engine_play()

    def stop_playback(self):
        """Stop playback and pause any torrent transfer until play resumes."""
        if hasattr(self, "engine") and self.engine is not None:
            self.engine.stop()
        if self.torrent_streamer:
            self.torrent_streamer.pause_transfer()

    def toggle_mute(self):
        """Toggle mute via native engine without fighting the volume slider."""
        if not hasattr(self, "engine") or self.engine is None:
            return
        muted = not self.engine.is_muted()
        self.engine.set_muted(muted)
        self.controls.btn_mute.setText("🔇" if muted else "🔊")
        self.controls.btn_mute.setToolTip("Unmute" if muted else "Mute")
        # Keep audible volume property intact while muted
        self._apply_output_gain_from_state()

    def _apply_output_gain_from_state(self):
        """Apply persisted 0..200 user volume via native engine only."""
        if hasattr(self, "engine") and self.engine is not None:
            self.engine.set_volume_percent(int(self.app_state.volume))

    def set_volume(self, volume):
        """Set volume (0-200) via native engine; Media Info reports the same %."""
        volume = max(0, min(200, int(volume)))
        gain = volume / 100.0

        # Persist logical volume so keyboard/slider/Media Info stay in sync.
        # 0% must remain 0 (never coerced via truthiness to a default).
        self.app_state.volume = volume
        self.base_volume = min(1.0, gain)
        self.volume_amplification = gain

        self._apply_output_gain_from_state()
        self.controls.volume_label.setText(f"{volume}%")
        # Keep slider aligned when volume is set from keyboard shortcuts
        if self.controls.volume_slider.value() != volume:
            self.controls.volume_slider.blockSignals(True)
            self.controls.volume_slider.setValue(volume)
            self.controls.volume_slider.blockSignals(False)

        # Persist immediately so the next launch restores the last volume.
        try:
            self.settings.settings.setValue("volume", volume)
            self.settings.settings.sync()
        except Exception:
            pass

        if volume > 100:
            self.status_bar.showMessage(
                f"Volume: {volume}% (engine boost — clipping may occur)",
                2500,
            )

    def adjust_volume(self, delta):
        """Adjust volume by delta"""
        # Use the logical app volume so 101-200% amplification is preserved.
        current_volume = int(self.app_state.volume)
        new_volume = max(0, min(200, current_volume + delta))
        self.controls.volume_slider.setValue(int(new_volume))
        self.set_volume(int(new_volume))

    def seek_to_position(self, position, exact: bool = True):
        """Seek to position (0.0-1.0). Scrub uses exact=False to avoid UI freezes."""
        if hasattr(self, "engine") and self.engine is not None:
            dur = self.engine.duration()
            if dur > 0:
                self.engine.set_position(int(position * dur), exact=exact)

    def seek_relative(self, seconds):
        """Seek relative to current position"""
        if hasattr(self, "engine") and self.engine is not None:
            self.engine.seek_relative(seconds)

    def take_snapshot(self):
        """Take a snapshot of the current frame"""
        # This would require video sink implementation
        self.status_bar.showMessage("Snapshot functionality not yet implemented")

    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
            self.controls.show()
            self.controls_visible = True
        else:
            self.showFullScreen()
            # Start auto-hide timer in fullscreen
            self.mouse_timer.start(3000)  # Hide after 3 seconds


    def show_controls(self):
        """Show control bar"""
        if not self.controls_visible:
            self.controls.show()
            self.controls_visible = True

    def hide_controls(self):
        """Hide control bar (only in fullscreen)"""
        if self.isFullScreen() and self.controls_visible:
            self.controls.hide()
            self.controls_visible = False

    def toggle_playlist(self):
        """Focus Up next (right Queue dock removed)."""
        self.focus_queue_panel()

    def hide_playlist(self):
        """No-op — Queue dock removed; Up next stays in Now Playing."""
        return

    def show_playlist(self):
        """Focus Up next in Now Playing (Queue dock removed)."""
        self.focus_queue_panel()

    def show_timeline_preview(self, show):
        """Show or hide timeline preview"""
        duration = self.engine.duration() if hasattr(self, "engine") and self.engine else 0
        if show and duration > 0:
            self.timeline_preview.show()
        else:
            self.timeline_preview.hide()

    def update_timeline_preview(self, position):
        """Update timeline preview with time information"""
        duration = self.engine.duration() if hasattr(self, "engine") and self.engine else 0
        if duration > 0:
            # Calculate time at this position
            time_ms = int(position * duration)
            total_ms = duration

            # Format current time
            current_seconds = time_ms // 1000
            current_minutes = current_seconds // 60
            current_seconds = current_seconds % 60

            # Format total time
            total_seconds = total_ms // 1000
            total_minutes = total_seconds // 60
            total_seconds = total_seconds % 60

            # Update preview text with progress
            time_text = f"{current_minutes:02d}:{current_seconds:02d} / {total_minutes:02d}:{total_seconds:02d}"
            self.timeline_preview.setText(time_text)

            # Position the preview near the seek bar
            if hasattr(self, 'last_mouse_pos'):
                # Position above the seek bar
                x = max(10, min(self.width() - 200, self.last_mouse_pos.x() - 50))
                y = self.controls.y() - 40
                self.timeline_preview.move(x, y)

    def mouseMoveEvent(self, event):
        """Handle mouse movement for auto-hide controls and timeline preview"""
        # Store mouse position for timeline preview (convert to int)
        self.last_mouse_pos = event.position().toPoint()

        if self.isFullScreen():
            self.show_controls()
            # Restart the hide timer
            self.mouse_timer.start(3000)
        super().mouseMoveEvent(event)

    def position_changed(self, position):
        """Handle position changes"""
        duration = self.engine.duration() if hasattr(self, "engine") else self.media_player.duration()
        self.controls.update_seek_position(position / duration if duration > 0 else 0)
        self.subtitle_manager.update_position(position)

    def duration_changed(self, duration):
        """Handle duration changes"""
        self.controls.update_time(0, duration)

    def playback_state_changed(self, state):
        """Handle playback state changes (engine string states)."""
        playing = False
        paused = False
        stopped = False
        if isinstance(state, str):
            playing = state == "playing"
            paused = state == "paused"
            stopped = state == "stopped"
        elif state is None and hasattr(self, "engine") and self.engine is not None:
            playing = self.engine.is_playing()
            paused = not playing and bool(self.engine.source_path())
            stopped = not playing and not paused
        else:
            stopped = True

        is_video = False
        if self.app_state.last_file:
            is_video = self.is_video_path(self.app_state.last_file)

        if playing:
            self.controls.btn_play.setText("⏸")
            self.status_bar.showMessage("Playing")
            self.show_logo(False)
        elif paused:
            self.controls.btn_play.setText("▶")
            self.status_bar.showMessage("Paused")
            # Keep video frame visible while paused; logo only for audio/empty.
            self.show_logo(False if is_video else True)
        else:
            self.controls.btn_play.setText("▶")
            self.status_bar.showMessage("Stopped")
            self.show_logo(True)

        if stopped:
            self.auto_play_next()

    def auto_play_next(self):
        """Advance when a track ends, honoring repeat / shuffle."""
        if not hasattr(self, "playlist") or self.playlist is None or self.playlist.count() == 0:
            return
        mode = self.app_state.repeat_mode or "off"
        if mode == "one" and self.app_state.last_file:
            path = self.app_state.last_file
            if os.path.exists(path):
                self.load_media(path)
                self.status_bar.showMessage(
                    f"Repeating: {os.path.basename(path)}", 3000
                )
                QTimer.singleShot(100, self._engine_play)
            return
        idx = self._queue_index_for_step(1)
        if idx is None:
            return
        path = self.playlist.get_file_at_index(idx)
        if path:
            self.playlist.setCurrentRow(idx)
            self.load_media(path)
            self.status_bar.showMessage(f"Auto-playing: {os.path.basename(path)}", 3000)
            QTimer.singleShot(100, self._engine_play)

    def media_error(self, error, error_string):
        """Surface native-engine failures; never fall back to another media stack."""
        if not error_string:
            return
        # Suppress common non-fatal decoder chatter
        if "pts == AV_NOPTS_VALUE" in error_string:
            return
        if "Unknown property transform" in error_string:
            return
        lower = error_string.lower()
        codecish = any(
            k in lower
            for k in (
                "codec",
                "unsupported",
                "no suitable",
                "could not demux",
                "cannot find",
                "format",
                "decoder",
                "demux",
                "native media core could not play",
                "encountered error",
                "decoder_or_demux",
                "load_failed",
            )
        )
        title = "Playback error (native engine)" if codecish else "Media Error"
        body = error_string
        if codecish and "Supported formats:" not in error_string:
            body = (
                f"{error_string}\n\n"
                f"{self._supported_formats_hint()}\n"
                "There is no alternate engine in VoxPlayer — fix codecs/plugins "
                "or choose a supported file."
            )
        # Avoid stacking identical modals for the same source
        if getattr(self, "_last_media_error_body", None) == body:
            self.status_bar.showMessage(error_string.split("\n", 1)[0][:120], 6000)
            return
        self._last_media_error_body = body
        QMessageBox.warning(self, title, body)
        self.status_bar.showMessage(error_string.split("\n", 1)[0][:120], 8000)

    def update_ui(self):
        """Update UI elements"""
        if not hasattr(self, "engine") or self.engine is None:
            return
        duration = self.engine.duration()
        if duration > 0:
            current_pos = self.engine.position()
            self.controls.update_time(current_pos, duration)

    def show_media_info(self):
        """Show media information dialog"""
        if not self.app_state.last_file:
            QMessageBox.information(self, "Media Info", "No media file loaded.")
            return

        try:
            file_path = self.app_state.last_file
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            file_size_mb = file_size / (1024 * 1024)
            file_ext = os.path.splitext(file_path)[1].upper()

            if hasattr(self, "engine") and self.engine is not None:
                duration = self.engine.duration()
                position = self.engine.position()
                state = "Playing" if self.engine.is_playing() else "Paused/Stopped"
                muted = self.engine.is_muted()
                embed = "embedded video" if self.engine.has_embedded_video else "audio path"
                engine_label = f"native C core ({embed})"
            else:
                duration = 0
                position = 0
                state = "Stopped"
                muted = False
                engine_label = "unavailable"

            duration_min = duration // 60000
            duration_sec = (duration % 60000) // 1000
            # Always report logical UI volume (0..200), not Qt's clamped 0..1.
            volume_pct = int(self.app_state.volume)
            if hasattr(self, "engine"):
                volume_pct = int(self.engine.volume_percent())

            meta = self._meta_cache.get(file_path)
            meta_block = ""
            if meta:
                meta_block = f"""
Enriched Metadata:
Title: {meta.display_title()}
Artist: {meta.artist or '—'}
Album: {meta.album or '—'}
Year: {meta.year or '—'}
Source: {meta.source}
"""

            info_text = f"""
Media Information:

File: {os.path.basename(file_path)}
Path: {file_path}
Size: {file_size_mb:.2f} MB
Format: {file_ext}
Duration: {duration_min}:{duration_sec:02d}
Volume: {volume_pct}%
Muted: {'Yes' if muted else 'No'}
Engine: {engine_label}
{meta_block}
Player Status:
State: {state}
Position: {position // 1000}s
            """

            QMessageBox.information(self, "Media Information", info_text)

        except Exception as e:
            QMessageBox.warning(self, "Media Info Error", f"Could not retrieve media information:\n{str(e)}")

    def show_about(self):
        """Show modern About modal."""
        dlg = AboutDialog(self.current_version, self)
        dlg.exec()

    def setup_system_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = self.windowIcon()
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("VoxPlayer")
        menu = QMenu()
        show_act = menu.addAction("Show VoxPlayer")
        show_act.triggered.connect(self.restore_from_tray)
        play_act = menu.addAction("Play / Pause")
        play_act.triggered.connect(self.toggle_playback)
        menu.addSeparator()
        quit_act = menu.addAction("Quit")
        quit_act.triggered.connect(self.quit_application)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

    def _tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.restore_from_tray()

    def hide_to_tray(self):
        if self.tray_icon is None:
            self.showMinimized()
            return
        self.hide()
        self.tray_icon.showMessage(
            "VoxPlayer",
            "Playing in the background. Click the tray icon to restore.",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )
        self.status_bar.showMessage("Minimized to tray — playback continues.", 3000)

    def restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_application(self):
        self._close_to_tray = False
        self.close()

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized() and self._close_to_tray and self.tray_icon is not None:
                QTimer.singleShot(0, self.hide_to_tray)
        super().changeEvent(event)

    def _queue_library_media_work(self, path: str) -> None:
        """Enqueue native (or sync fallback) thumbnail + local tags for a library path."""
        if not path or not os.path.isfile(path):
            return
        workers = getattr(self, "native_workers", None)
        if workers is not None and workers.available:
            workers.submit_thumb(path, _thumb_cache_root(), seek=3.0)
            if path not in self._meta_cache:
                workers.submit_tags(path)
            return
        # Sync Python fallback when the Rust pool is not built.
        try:
            generated = self.thumb_cache.ensure(path)
            if generated:
                self._thumb_map[path] = generated
                if hasattr(self, "home_view"):
                    self.home_view.update_thumbnail(path, generated)
        except Exception:
            pass
        if path not in self._meta_cache:
            try:
                self._meta_cache[path] = load_local_metadata(path)
            except Exception:
                pass

    def _on_native_thumb_ready(self, path: str, thumb_path: str) -> None:
        if not path or not thumb_path:
            return
        self._thumb_map[path] = thumb_path
        if hasattr(self, "home_view"):
            self.home_view.update_thumbnail(path, thumb_path)

    def _on_native_tags_ready(self, path: str, tags: dict) -> None:
        if not path or not isinstance(tags, dict):
            return
        existing = self._meta_cache.get(path)
        meta = existing or MediaMetadata(path=path, source="native")
        meta.path = path
        meta.title = (tags.get("title") or meta.title or "").strip()
        meta.artist = (tags.get("artist") or meta.artist or "").strip()
        meta.album = (tags.get("album") or meta.album or "").strip()
        meta.year = (tags.get("year") or meta.year or "")[:4]
        meta.genre = (tags.get("genre") or meta.genre or "").strip()
        if meta.title or meta.artist:
            meta.source = "tags"
        self._meta_cache[path] = meta
        if getattr(self.home_view, "_browse_mode", False):
            self.refresh_facets()

    def _setup_mpris_and_daemon(self) -> None:
        """Start MPRIS2 (Linux) and optional localhost control daemon."""
        def _raise_window():
            self.showNormal()
            self.raise_()
            self.activateWindow()

        def _set_shuffle(value: bool):
            self.app_state.shuffle_enabled = bool(value)
            self.settings.save_state(self.app_state)
            if hasattr(self, "controls"):
                self.controls.sync_playback_modes(
                    self.app_state.shuffle_enabled, self.app_state.repeat_mode
                )

        self.mpris.set_callbacks(
            raise_window=_raise_window,
            quit_app=self.close,
            play=self._engine_play,
            pause=lambda: self.engine.pause() if hasattr(self, "engine") else None,
            play_pause=self.toggle_playback,
            stop=self.stop_playback,
            next=self.next_media,
            previous=self.previous_media,
            open_uri=lambda uri: self.load_and_play_media(
                QUrl(uri).toLocalFile() or uri
            ),
            playback_status=self._mpris_playback_status,
            loop_status=self._mpris_loop_status,
            set_loop_status=self._mpris_set_loop_status,
            shuffle=lambda: bool(self.app_state.shuffle_enabled),
            set_shuffle=_set_shuffle,
            metadata=self._mpris_metadata,
            volume=lambda: (self.engine.volume_percent() / 100.0)
            if hasattr(self, "engine") and self.engine
            else 1.0,
            set_volume=lambda v: self.set_volume(int(max(0.0, min(2.0, float(v))) * 100)),
            position_us=lambda: int(self.engine.position() * 1000)
            if hasattr(self, "engine") and self.engine
            else 0,
            seek_us=lambda off: self.engine.seek_relative(off / 1_000_000.0)
            if hasattr(self, "engine") and self.engine
            else None,
            set_position_us=lambda pos: self.engine.set_position(int(pos / 1000), exact=True)
            if hasattr(self, "engine") and self.engine
            else None,
        )
        if self.mpris.start():
            self.status_bar.showMessage("MPRIS2 desktop controls enabled", 3000)

        def _ok(fn):
            def _wrap(*a, **k):
                fn(*a, **k)
                return {"ok": True}

            return _wrap

        self.control_daemon.set_callbacks(
            status=self._daemon_status,
            play=_ok(self._engine_play),
            pause=_ok(lambda: self.engine.pause() if hasattr(self, "engine") else None),
            play_pause=_ok(self.toggle_playback),
            stop=_ok(self.stop_playback),
            next=_ok(self.next_media),
            previous=_ok(self.previous_media),
            volume=self._daemon_set_volume,
            seek=self._daemon_seek,
            open=self._daemon_open,
        )
        if self.control_daemon.start():
            self.status_bar.showMessage(
                f"Control daemon http://{self.control_daemon.host}:{self.control_daemon.port}/",
                4000,
            )

    def _mpris_playback_status(self) -> str:
        if not hasattr(self, "engine") or self.engine is None:
            return "Stopped"
        if self.engine.is_playing():
            return "Playing"
        # paused vs stopped
        st = getattr(self.engine, "_last_state", "") or ""
        if st == "paused":
            return "Paused"
        return "Stopped"

    def _mpris_loop_status(self) -> str:
        mode = self.app_state.repeat_mode or "off"
        return {"off": "None", "all": "Playlist", "one": "Track"}.get(mode, "None")

    def _mpris_set_loop_status(self, value: str) -> None:
        mapping = {"None": "off", "Playlist": "all", "Track": "one"}
        self.app_state.repeat_mode = mapping.get(value, "off")
        self.settings.save_state(self.app_state)
        if hasattr(self, "controls"):
            self.controls.sync_playback_modes(
                self.app_state.shuffle_enabled, self.app_state.repeat_mode
            )

    def _mpris_metadata(self) -> dict:
        path = self.app_state.last_file or ""
        meta = self._meta_cache.get(path)
        title = (meta.title if meta and meta.title else None) or (
            os.path.basename(path) if path else "VoxPlayer"
        )
        artist = (meta.artist if meta and meta.artist else "") or ""
        album = (meta.album if meta and meta.album else "") or ""
        length = 0
        if hasattr(self, "engine") and self.engine is not None:
            length = int(self.engine.duration() * 1000)  # microseconds
        track_id = f"/org/voxplayer/track/{abs(hash(path)) & 0xFFFFFFFF}"
        out = {
            "mpris:trackid": track_id,
            "xesam:title": title,
            "mpris:length": length,
        }
        if artist:
            out["xesam:artist"] = [artist]
        if album:
            out["xesam:album"] = album
        if path:
            out["xesam:url"] = QUrl.fromLocalFile(os.path.abspath(path)).toString()
        return out

    def _daemon_status(self) -> dict:
        path = self.app_state.last_file or ""
        return {
            "playing": bool(hasattr(self, "engine") and self.engine and self.engine.is_playing()),
            "path": path,
            "position_ms": int(self.engine.position())
            if hasattr(self, "engine") and self.engine
            else 0,
            "duration_ms": int(self.engine.duration())
            if hasattr(self, "engine") and self.engine
            else 0,
            "volume_percent": int(self.engine.volume_percent())
            if hasattr(self, "engine") and self.engine
            else int(self.app_state.volume),
            "shuffle": bool(self.app_state.shuffle_enabled),
            "repeat": self.app_state.repeat_mode,
            "version": self.current_version,
        }

    def _daemon_set_volume(self, body: dict) -> dict:
        pct = int(body.get("percent", self.app_state.volume))
        self.set_volume(pct)
        return {"ok": True, "percent": pct}

    def _daemon_seek(self, body: dict) -> dict:
        if not hasattr(self, "engine") or self.engine is None:
            return {"ok": False}
        if "relative_ms" in body:
            self.engine.seek_relative(float(body["relative_ms"]) / 1000.0)
        elif "ms" in body:
            self.engine.set_position(int(body["ms"]), exact=True)
        return {"ok": True, "position_ms": int(self.engine.position())}

    def _daemon_open(self, body: dict) -> dict:
        path = str(body.get("path") or "")
        if not path:
            return {"ok": False, "error": "path required"}
        self.load_and_play_media(path)
        return {"ok": True, "path": path}

    def subscribe_podcast_feed(self) -> None:
        url, ok = QInputDialog.getText(
            self, "Subscribe to podcast", "RSS / Atom feed URL:"
        )
        if not ok or not (url or "").strip():
            return
        try:
            feed = self.podcast_store.subscribe(url.strip())
            QMessageBox.information(
                self,
                "Podcast subscribed",
                f"{feed.title}\n{len(feed.episodes)} episode(s) listed.\n"
                "Use Podcasts → Browse / Download Episodes to fetch audio.",
            )
            self.status_bar.showMessage(f"Subscribed: {feed.title}", 4000)
        except Exception as exc:
            QMessageBox.warning(self, "Subscribe failed", str(exc))

    def refresh_podcast_feeds(self) -> None:
        if not self.podcast_store.feeds:
            QMessageBox.information(self, "Podcasts", "No feeds subscribed yet.")
            return
        feeds = self.podcast_store.refresh()
        self.status_bar.showMessage(f"Refreshed {len(feeds)} podcast feed(s)", 4000)

    def browse_podcast_episodes(self) -> None:
        if not self.podcast_store.feeds:
            QMessageBox.information(
                self,
                "Podcasts",
                "No feeds yet. Use Podcasts → Subscribe to Feed… first.",
            )
            return
        feed_titles = {f"{f.title} ({f.url})": f for f in self.podcast_store.feeds.values()}
        label, ok = QInputDialog.getItem(
            self, "Podcast feed", "Select feed:", list(feed_titles.keys()), 0, False
        )
        if not ok or label not in feed_titles:
            return
        feed = feed_titles[label]
        if not feed.episodes:
            QMessageBox.information(self, "Podcasts", "No episodes with audio enclosures.")
            return
        choices = [
            f"{i+1}. {ep.title}" + (" ✓" if ep.local_path and os.path.isfile(ep.local_path) else "")
            for i, ep in enumerate(feed.episodes[:80])
        ]
        pick, ok = QInputDialog.getItem(
            self, feed.title, "Download & play episode:", choices, 0, False
        )
        if not ok or not pick:
            return
        idx = choices.index(pick)
        ep = feed.episodes[idx]
        try:
            self.status_bar.showMessage(f"Downloading: {ep.title}", 0)
            QApplication.processEvents()
            path = download_episode(ep, feed.title)
            self.podcast_store.save()
            self._register_library_path(path)
            self._remember_library_root(podcasts_dir())
            self.refresh_home_grid()
            self.load_and_play_media(path)
            self.status_bar.showMessage(f"Playing podcast: {ep.title}", 5000)
        except Exception as exc:
            QMessageBox.warning(self, "Download failed", str(exc))

    def closeEvent(self, event):
        """Close-to-tray while playing; otherwise persist state and quit."""
        playing = False
        if hasattr(self, "engine"):
            playing = self.engine.is_playing()
        if self._close_to_tray and self.tray_icon is not None and playing:
            event.ignore()
            self.hide_to_tray()
            return
        self.app_state.window_geometry = self.saveGeometry()
        self.settings.save_state(self.app_state)
        if hasattr(self, "mpris") and self.mpris is not None:
            self.mpris.stop()
        if hasattr(self, "control_daemon") and self.control_daemon is not None:
            self.control_daemon.stop()
        if hasattr(self, "native_workers") and self.native_workers is not None:
            self.native_workers.shutdown()
        if hasattr(self, "engine"):
            self.engine.shutdown()
        if self.tray_icon is not None:
            self.tray_icon.hide()
        event.accept()

def main():
    # Prefer X11/XWayland so native window-ID video embed works; volume 0–200% via engine-native API.
    prefer_xcb_for_mpv_embed()
    # Suppress verbose console output
    os.environ['QT_LOGGING_RULES'] = 'qt.multimedia.ffmpeg.debug=false'
    # native C media core is the only playback engine (no Qt Multimedia playback fallback)
    os.environ["VOXPLAYER_ENGINE"] = "native"

    app = QApplication(sys.argv)
    app.setApplicationName("VoxPlayer")
    app.setApplicationVersion("1.13.0")
    app.setQuitOnLastWindowClosed(False)

    # Set application properties
    app.setOrganizationName("VoxHash")
    app.setOrganizationDomain("voxhash.dev")

    # Set application icon
    try:
        # Try to load icon from package directory first
        icon_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if not os.path.exists(icon_path):
            # Fallback to current directory
            icon_path = "logo.png"
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        print(f"Warning: Could not load application icon: {e}")

    # Check for command-line arguments (file to open)
    file_to_open = None
    if len(sys.argv) > 1:
        file_to_open = sys.argv[1]
        # Validate the file exists and is a supported media file
        if os.path.exists(file_to_open):
            # Check if it's a supported media file
            supported_extensions = [
                '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v',  # Video
                '.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac', '.wma'  # Audio
            ]
            file_ext = os.path.splitext(file_to_open)[1].lower()
            if file_ext in supported_extensions:
                file_to_open = os.path.abspath(file_to_open)  # Convert to absolute path
            else:
                print(f"Warning: Unsupported file format: {file_ext}")
                file_to_open = None
        else:
            print(f"Warning: File not found: {file_to_open}")
            file_to_open = None

    try:
        window = VoxPlayerMainWindow(file_to_open)
    except NativeEngineError as exc:
        show_native_engine_failure(str(exc))
        sys.exit(1)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()


