#!/usr/bin/env python3
"""
VoxPlayer - A modern multimedia player built with PyQt6
Clean implementation without signal issues
"""

import sys
import os
import tempfile
import shutil
import requests
import webbrowser
import json
import re
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QSlider, QLabel,
                            QFileDialog, QDockWidget, QListWidget, QListWidgetItem,
                            QMenuBar, QMenu, QStatusBar, QMessageBox, QInputDialog,
                            QLineEdit, QStackedWidget, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QSettings, QUrl, QThread, pyqtSignal
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QKeySequence, QShortcut, QAction, QIcon, QPixmap

from .theme import app_stylesheet, COLORS
from .ui.shell import LeftRail, HomeView, NowPlayingPanel, TransportBar
from .engine.playback import PlaybackEngine
from .media.thumbnails import ThumbnailCache, get_thumbnail_path
from .media.metadata import MediaMetadata, enrich_metadata
from .media.torrent_gate import validate_torrent_file, validate_torrent_file_list


class MetadataEnrichWorker(QThread):
    """Background tag / MusicBrainz / AcoustID / TMDB enrichment."""

    finished_meta = pyqtSignal(object)

    def __init__(self, path: str, cover_path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.cover_path = cover_path

    def run(self):
        try:
            meta = enrich_metadata(self.path, cover_dest=self.cover_path)
        except Exception:
            meta = MediaMetadata(path=self.path)
        self.finished_meta.emit(meta)


# Data classes for state management
@dataclass
class AppState:
    window_geometry: Optional[bytes] = None
    theme: str = "dark"
    volume: int = 50
    last_file: str = ""
    resume_positions: Dict[str, int] = None
    auto_update_enabled: bool = True
    update_channel: str = "stable"
    audio_output_mode: str = "default"  # "default" or "manual"
    selected_audio_device: str = ""  # Device ID for manual mode

    def __post_init__(self):
        if self.resume_positions is None:
            self.resume_positions = {}

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

    def __init__(self, magnet_link: str = None, torrent_file: str = None):
        super().__init__()
        self.magnet_link = magnet_link
        self.torrent_file = torrent_file
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
                f"Failed to connect to qBittorrent at '{os.getenv('QB_HOST', 'localhost:8080')}'. "
                "Please ensure qBittorrent is running, Web UI is enabled, and QB_USERNAME/QB_PASSWORD are set if auth is required."
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
                torrent_info = self.qb_client.torrents_add(**add_kwargs)
            except TypeError:
                add_kwargs.pop("is_sequential_download", None)
                add_kwargs.pop("is_first_last_piece_prio", None)
                torrent_info = self.qb_client.torrents_add(**add_kwargs)

            if self._torrent_add_succeeded(torrent_info):
                self.progress_updated.emit(30, "Torrent file added successfully")
                self._monitor_torrent()
            else:
                self.error_occurred.emit(f"Failed to add torrent file: {torrent_info}")

        except Exception as e:
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

        self._prioritize_selected_file(file_index)
        self.progress_updated.emit(
            45,
            f"Sequential mode enabled for {os.path.basename(file_name)}",
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
        """Select best candidate for immediate playback (prefer MP4, then largest)."""
        files = self._torrent_files()
        if not files:
            return None

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

    def _prioritize_selected_file(self, selected_index: int):
        """Download selected media file first to reduce startup delay."""
        file_items = self._torrent_files()
        selected_ids = []
        other_ids = []
        for item in file_items:
            idx = self._file_index(item)
            if idx is None:
                continue
            if idx == selected_index:
                selected_ids.append(idx)
            else:
                other_ids.append(idx)

        if selected_ids:
            try:
                self.qb_client.torrents_file_priority(
                    torrent_hash=self.torrent_hash, file_ids=selected_ids, priority=7
                )
            except Exception:
                pass
        if other_ids:
            try:
                self.qb_client.torrents_file_priority(
                    torrent_hash=self.torrent_hash, file_ids=other_ids, priority=0
                )
            except Exception:
                pass

    def _buffer_target_bytes(self) -> int:
        """Compute startup buffer based on file size/container."""
        if self.stream_file_size <= 0 or not self.stream_file_path:
            return 0
        _, ext = os.path.splitext(self.stream_file_path.lower())
        base = 64 * 1024 * 1024 if ext == ".mkv" else 32 * 1024 * 1024
        pct_target = int(self.stream_file_size * 0.02)
        return min(max(base, pct_target), 256 * 1024 * 1024)

    def _is_buffer_ready(self):
        """Return whether selected file has enough sequentially downloaded data."""
        if self.stream_file_index is None:
            return False, 0, 0
        required = self._buffer_target_bytes()
        for item in self._torrent_files():
            idx = self._file_index(item)
            if idx == self.stream_file_index:
                size = int(getattr(item, "size", 0) or 0)
                progress = float(getattr(item, "progress", 0.0) or 0.0)
                downloaded = int(size * progress)
                return downloaded >= required, downloaded, required
        return False, 0, required

    def stop(self):
        """Stop torrent streaming"""
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
        self.settings.setValue("resume_positions", json.dumps(state.resume_positions))
        self.settings.setValue("audio_output_mode", state.audio_output_mode)
        self.settings.setValue("selected_audio_device", state.selected_audio_device)

    def load_state(self) -> AppState:
        """Load application state"""
        return AppState(
            window_geometry=self.settings.value("window_geometry"),
            theme=self.settings.value("theme", "dark"),
            volume=int(self.settings.value("volume", 50)),
            last_file=self.settings.value("last_file", ""),
            resume_positions=json.loads(self.settings.value("resume_positions", "{}")),
            audio_output_mode=self.settings.value("audio_output_mode", "default"),
            selected_audio_device=self.settings.value("selected_audio_device", "")
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
                    QTimer.singleShot(100, self.parent_window.media_player.play)

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

    def load_subtitles(self, file_path):
        """Load SRT subtitle file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.current_subtitles = self.parse_srt(content)
            return True
        except Exception as e:
            print(f"Error loading subtitles: {e}")
            return False

    def parse_srt(self, content):
        """Parse SRT subtitle content"""
        # Clean line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        # Split into blocks
        blocks = content.strip().split('\n\n')
        subtitles = []

        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    # Parse time
                    time_line = lines[1]
                    start_time, end_time = self.parse_time_range(time_line)

                    # Parse text
                    text = '\n'.join(lines[2:])

                    subtitles.append({
                        'start': start_time,
                        'end': end_time,
                        'text': text
                    })
                except Exception as e:
                    print(f"Error parsing subtitle block: {e}")
                    continue

        return subtitles

    def parse_time_range(self, time_str):
        """Parse SRT time format (HH:MM:SS,mmm --> HH:MM:SS,mmm)"""
        try:
            start_str, end_str = time_str.split(' --> ')
            start_time = self.parse_time(start_str.strip())
            end_time = self.parse_time(end_str.strip())
            return start_time, end_time
        except Exception as e:
            print(f"Error parsing time range: {e}")
            return 0, 0

    def parse_time(self, time_str):
        """Parse SRT time format (HH:MM:SS,mmm) to milliseconds"""
        try:
            # Remove milliseconds part
            time_part, ms_part = time_str.split(',')
            hours, minutes, seconds = map(int, time_part.split(':'))
            milliseconds = int(ms_part)

            total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
            return total_ms
        except Exception as e:
            print(f"Error parsing time: {e}")
            return 0

    def update_position(self, position_ms):
        """Update subtitle display based on current position"""
        self.current_position = position_ms

        # Find current subtitle
        current_subtitle = None
        for subtitle in self.current_subtitles:
            if subtitle['start'] <= position_ms <= subtitle['end']:
                current_subtitle = subtitle
                break

        if current_subtitle:
            self.subtitle_label.setText(current_subtitle['text'])
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
        self.update_checker = None
        self.current_version = "1.1.1"
        self.thumb_cache = ThumbnailCache()
        self._meta_cache: Dict[str, MediaMetadata] = {}
        self._thumb_map: Dict[str, str] = {}
        self._preview_timer = None
        self._enrich_thread = None

        # Audio device detection
        self.current_audio_device = None
        self.audio_device_timer = None
        self.available_audio_devices = []
        self.audio_device_menu = None

        self.setup_ui()
        self.setup_media_player()
        self.setup_shortcuts()
        self.setup_timers()
        self.setup_drag_drop()
        self.setup_auto_update()
        self.apply_theme()
        self.setup_icon()

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
        self.left_rail.queue_requested.connect(self.focus_queue_panel)
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

        self.stage_page = QWidget()
        stage_layout = QVBoxLayout(self.stage_page)
        stage_layout.setContentsMargins(12, 12, 12, 8)
        stage_layout.setSpacing(0)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("QVideoWidget { background-color: #000000; border-radius: 10px; }")
        self.video_widget.setAcceptDrops(True)
        self.video_widget.mouseDoubleClickEvent = lambda event: self.toggle_fullscreen()
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        stage_layout.addWidget(self.video_widget)
        self.center_stack.addWidget(self.home_view)
        self.center_stack.addWidget(self.stage_page)
        center_layout.addWidget(self.center_stack, 1)
        body_layout.addWidget(center, 1)

        self.now_playing = NowPlayingPanel(self)
        body_layout.addWidget(self.now_playing)

        shell_layout.addWidget(body, 1)

        self.controls = TransportBar(self)
        shell_layout.addWidget(self.controls)

        self.playlist = PlaylistWidget(self)
        self.playlist_dock = QDockWidget("Queue")
        playlist_container = QWidget()
        playlist_layout = QVBoxLayout(playlist_container)
        playlist_layout.setContentsMargins(0, 0, 0, 0)
        playlist_layout.setSpacing(2)
        self.playlist_search = QLineEdit()
        self.playlist_search.setPlaceholderText("Search queue...")
        self.playlist_search.setObjectName("SearchField")
        self.playlist_search.textChanged.connect(self.filter_playlist)
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(4, 4, 4, 0)
        search_layout.setSpacing(2)
        search_layout.addWidget(self.playlist_search)
        self.clear_search_btn = QPushButton("✕")
        self.clear_search_btn.setFixedSize(24, 24)
        self.clear_search_btn.clicked.connect(self.clear_playlist_search)
        search_layout.addWidget(self.clear_search_btn)
        playlist_layout.addWidget(search_container)
        playlist_layout.addWidget(self.playlist)
        self.playlist_dock.setWidget(playlist_container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.playlist_dock)
        self.playlist_dock.hide()
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
            self.refresh_home_grid()

    def show_shell_page(self, page: str):
        if page in ("home", "library"):
            self.shell_mode = "home"
            self.center_stack.setCurrentWidget(self.home_view)
            self.left_rail.set_active("library" if page == "library" else "home")
            self.refresh_home_grid()
        else:
            self.shell_mode = "stage"
            self.center_stack.setCurrentWidget(self.stage_page)

    def focus_queue_panel(self):
        self.left_rail.set_active("queue")
        self.toggle_now_playing(True)
        self.show_playlist()

    def toggle_now_playing(self, force=None):
        visible = (not self.now_playing_visible) if force is None else bool(force)
        self.now_playing.setVisible(visible)
        self.now_playing_visible = visible

    def _register_library_path(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            return
        if file_path not in self.library_paths:
            self.library_paths.insert(0, file_path)

    def refresh_home_grid(self, filter_name: str = None, query: str = None):
        filter_name = (filter_name or getattr(self, "_home_filter", "all")).lower()
        query = (query if query is not None else getattr(self, "_home_query", "")).lower()
        self._home_filter = filter_name
        self._home_query = query
        video_ext = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
        audio_ext = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma"}
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
        for path in filtered[:48]:
            cached = self._thumb_map.get(path) or get_thumbnail_path(path)
            if cached:
                thumbs[path] = cached
                self._thumb_map[path] = cached
            else:
                # Generate asynchronously-ish for first batch (fast ffmpeg seeks)
                try:
                    generated = self.thumb_cache.ensure(path)
                    if generated:
                        thumbs[path] = generated
                        self._thumb_map[path] = generated
                except Exception:
                    pass
        self.home_view.set_items(filtered, thumbnails=thumbs)
        self.home_view.hint.setText(f"{len(filtered)} items")

    def apply_home_filter(self, name: str):
        self.refresh_home_grid(filter_name=name)

    def apply_home_search(self, text: str):
        self.refresh_home_grid(query=text)

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

        stop_torrent_action = QAction("&Stop Torrent", self)
        stop_torrent_action.setShortcut("Ctrl+Shift+T")
        stop_torrent_action.triggered.connect(self.stop_torrent)
        torrent_menu.addAction(stop_torrent_action)

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
        clear_playlist_action.triggered.connect(self.clear_playlist)
        playlists_menu.addAction(clear_playlist_action)

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

        # View menu - add playlist toggle
        playlist_action = QAction("&Queue Panel", self)
        playlist_action.setShortcut("Ctrl+L")
        playlist_action.setCheckable(True)
        playlist_action.setChecked(False)
        playlist_action.triggered.connect(self.toggle_playlist)
        view_menu.addAction(playlist_action)

        now_playing_action = QAction("&Now Playing", self)
        now_playing_action.setShortcut("Ctrl+Shift+N")
        now_playing_action.setCheckable(True)
        now_playing_action.setChecked(True)
        now_playing_action.triggered.connect(lambda: self.toggle_now_playing())
        view_menu.addAction(now_playing_action)

        home_action = QAction("&Home", self)
        home_action.setShortcut("Ctrl+H")
        home_action.triggered.connect(lambda: self.show_shell_page("home"))
        view_menu.addAction(home_action)

        # View menu - add media info
        view_menu.addSeparator()

        media_info_action = QAction("&Media Info", self)
        media_info_action.setShortcut("Ctrl+I")
        media_info_action.triggered.connect(self.show_media_info)
        view_menu.addAction(media_info_action)

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

        self.engine = PlaybackEngine(self.video_widget, self)
        self.media_player = self.engine.media_player
        self.audio_output = self.engine.audio_output

        self.engine.position_changed.connect(self.position_changed)
        self.engine.duration_changed.connect(self.duration_changed)
        self.engine.state_changed.connect(self._engine_state_changed)
        self.engine.error_occurred.connect(lambda msg: self.media_error(None, msg))
        self.engine.backend_ready.connect(self._on_backend_ready)
        self.media_player.playbackStateChanged.connect(self.playback_state_changed)

        self._apply_output_gain_from_state()
        self.controls.volume_slider.setValue(self.app_state.volume)
        self._on_backend_ready(self.engine.backend_name)

    def _on_backend_ready(self, name: str):
        label = "libmpv (HW)" if name == "mpv" else "Qt Multimedia"
        if hasattr(self, "now_playing"):
            self.now_playing.engine_label.setText(f"Engine: {label}")
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage(f"Playback engine: {label}", 4000)

    def _engine_state_changed(self, state: str):
        if state == "playing":
            self.controls.btn_play.setText("⏸")
            if self._preview_timer and not self._preview_timer.isActive():
                self._preview_timer.start()
            # Pulse sink-input often appears only after playback starts
            QTimer.singleShot(300, self._apply_output_gain_from_state)
        else:
            self.controls.btn_play.setText("▶")
            if state == "stopped" and self._preview_timer:
                self._preview_timer.stop()

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

        # Playlist toggle (handled by menu action)

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
        """Setup comprehensive drag and drop functionality for all app components"""
        # Enable drag and drop on the entire main window
        self.setAcceptDrops(True)
        self.video_widget.setAcceptDrops(True)

        # Enable on all major components
        if hasattr(self, 'centralWidget'):
            self.centralWidget().setAcceptDrops(True)
        if hasattr(self, 'controls'):
            self.controls.setAcceptDrops(True)
        if hasattr(self, 'status_bar'):
            self.status_bar.setAcceptDrops(True)

        # Enable drag and drop on the playlist dock and widget
        if hasattr(self, 'playlist_dock'):
            self.playlist_dock.setAcceptDrops(True)
        if hasattr(self, 'playlist'):
            self.playlist.setAcceptDrops(True)

        # Enable on menu bar and all dock widgets
        if hasattr(self, 'menuBar'):
            self.menuBar().setAcceptDrops(True)

        # Enable on all dock widgets
        for dock in self.findChildren(QDockWidget):
            dock.setAcceptDrops(True)

        # Enable on all child widgets recursively
        self._enable_drag_drop_recursive(self)

    def _enable_drag_drop_recursive(self, widget):
        """Recursively enable drag and drop on all child widgets"""
        try:
            # Enable drag and drop on this widget
            widget.setAcceptDrops(True)

            # Recursively enable on all children
            for child in widget.findChildren(QWidget):
                if child != widget:  # Avoid infinite recursion
                    child.setAcceptDrops(True)
        except Exception:
            # Silently handle any errors
            pass

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
        """Update the current audio output device"""
        try:
            if self.app_state.audio_output_mode == "default":
                # Use default device (simplified approach)
                if hasattr(self, 'audio_output'):
                    # Just recreate audio output to use default device
                    self.audio_output = QAudioOutput()
                    self.media_player.setAudioOutput(self.audio_output)
                    self._apply_output_gain_from_state()
                    self.status_bar.showMessage("Audio device: Default (Auto-adapt)")
            else:
                # Manual mode - for now just use default device
                if hasattr(self, 'audio_output'):
                    self.audio_output = QAudioOutput()
                    self.media_player.setAudioOutput(self.audio_output)
                    self._apply_output_gain_from_state()
                    self.status_bar.showMessage("Audio device: Manual selection")

        except Exception as e:
            self.status_bar.showMessage(f"Audio device error: {str(e)}")

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
• Ctrl+L: Toggle Playlist
• Ctrl+I: Import Playlist
• Ctrl+M: Open Magnet Link
• Ctrl+T: Open Torrent File
• Ctrl+E: Export Playlist
• Ctrl+Shift+C: Clear Playlist
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

    def open_magnet_link(self):
        """Open magnet link dialog"""
        magnet_link, ok = QInputDialog.getText(
            self, "Open Magnet Link", "Enter magnet link:"
        )
        if ok and magnet_link:
            self.start_torrent_streaming(magnet_link)

    def open_torrent_file(self):
        """Open torrent file dialog"""
        default_dir = os.path.expanduser("~/Downloads/Torrents")
        if not os.path.isdir(default_dir):
            default_dir = os.path.expanduser("~/Downloads")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Torrent File", default_dir, "Torrent Files (*.torrent)"
        )
        if file_path:
            self.start_torrent_streaming(torrent_file=file_path)

    def start_torrent_streaming(self, magnet_link: str = None, torrent_file: str = None):
        """Start torrent streaming"""
        if self.torrent_streamer and self.torrent_streamer.isRunning():
            QMessageBox.warning(self, "Torrent Active", "A torrent is already being streamed.")
            return

        # Gate .torrent files before contacting the client
        if torrent_file:
            ok, msg, _paths = validate_torrent_file(torrent_file)
            if not ok:
                QMessageBox.warning(
                    self,
                    "Torrent Rejected",
                    f"{msg}\n\nVoxPlayer only accepts torrents that look like a "
                    "video, music, or playlist media library.",
                )
                self.status_bar.showMessage("Torrent rejected: not a media library.")
                return

        self.torrent_streamer = TorrentStreamer(magnet_link=magnet_link, torrent_file=torrent_file)
        self.torrent_streamer.progress_updated.connect(self.on_torrent_progress)
        self.torrent_streamer.file_ready.connect(self.on_torrent_file_ready)
        self.torrent_streamer.error_occurred.connect(self.on_torrent_error)
        self.torrent_streamer.start()

        if magnet_link:
            self.status_bar.showMessage("Starting magnet link stream...")
        elif torrent_file:
            self.status_bar.showMessage("Starting torrent file stream...")

    def stop_torrent(self):
        """Stop torrent streaming"""
        if self.torrent_streamer and self.torrent_streamer.isRunning():
            self.torrent_streamer.stop()
            self.torrent_streamer.wait()
            self.status_bar.showMessage("Torrent stopped.")
        else:
            QMessageBox.information(self, "No Torrent", "No torrent is currently active.")

    def on_torrent_progress(self, progress: int, status: str):
        """Handle torrent progress updates"""
        self.status_bar.showMessage(f"Torrent: {status} ({progress}%)")

    def on_torrent_file_ready(self, file_path: str):
        """Handle torrent file ready"""
        # Add to playlist first
        self.playlist.add_media_file(file_path)
        self.playlist.setCurrentRow(self.playlist.count() - 1)

        # Load and play the media
        self.load_media(file_path)
        QTimer.singleShot(100, self.media_player.play)

        self.status_bar.showMessage(f"Torrent file ready: {os.path.basename(file_path)}")

    def on_torrent_error(self, error_message: str):
        """Handle torrent errors"""
        QMessageBox.warning(self, "Torrent Error", error_message)
        self.status_bar.showMessage("Torrent error occurred.")

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
            if hasattr(self, 'media_player'):
                self.media_player.stop()

            # Clear the playlist
            self.playlist.clear()

            # Reset app state
            self.app_state.last_file = ""
            self.setWindowTitle("VoxPlayer")

            # Clear search if active
            if hasattr(self, 'playlist_search'):
                self.playlist_search.clear()

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
        """Check for audio device changes and update audio output accordingly"""
        try:
            # Simple approach: Check if audio output is still working
            if hasattr(self, 'audio_output') and self.audio_output:
                # Try to get volume to test if device is still accessible
                current_volume = self.audio_output.volume()

                # If we can't get volume, the device might have changed
                if current_volume is None:
                    # Recreate audio output to use default device
                    self.audio_output = QAudioOutput()
                    self.media_player.setAudioOutput(self.audio_output)
                    self._apply_output_gain_from_state()

                    # Update status bar
                    self.status_bar.showMessage("Audio device updated")
                    QTimer.singleShot(3000, lambda: self.status_bar.showMessage("Ready"))

        except Exception as e:
            # Silently handle any errors in device detection
            pass

    def dragEnterEvent(self, event):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            # Check if any of the URLs is a supported media file or folder
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if self.is_supported_media_file(file_path) or os.path.isdir(file_path):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        """Handle drop events with enhanced support for multiple files/folders"""
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
                    folder_media = self.find_media_files_in_folder(file_path)
                    media_files.extend(folder_media)
                    folders_processed += 1
                    if folder_media:
                        self.status_bar.showMessage(f"Scanning folder: {os.path.basename(file_path)} ({len(folder_media)} files found)", 2000)
                elif self.is_supported_media_file(file_path):
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
                self.playlist.clear()
                for file_path in unique_media_files:
                    self.playlist.add_media_file(file_path)

                # Load and auto-play the first file
                if unique_media_files:
                    self.load_media(unique_media_files[0])
                    self.playlist.setCurrentRow(0)

                    # Auto-start playback
                    QTimer.singleShot(100, self.media_player.play)

                    # Show comprehensive status message
                    status_parts = []
                    if files_processed > 0:
                        status_parts.append(f"{files_processed} file{'s' if files_processed != 1 else ''}")
                    if folders_processed > 0:
                        status_parts.append(f"{folders_processed} folder{'s' if folders_processed != 1 else ''}")

                    status_msg = f"Loaded {len(unique_media_files)} media files from {', '.join(status_parts)}"
                    self.status_bar.showMessage(status_msg, 5000)

                    # Show playlist if it was hidden
                    if hasattr(self, 'playlist_dock') and self.playlist_dock.isHidden():
                        self.show_playlist()

                event.acceptProposedAction()
                return
        event.ignore()

    def find_media_files_in_folder(self, folder_path):
        """Find all supported media files in a folder recursively"""
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
        video_formats = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.3g2', '.mj2']

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
        """Apply VoxPlayer unique dark shell stylesheet."""
        self.setStyleSheet(app_stylesheet())

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
            "Audio Files (*.mp3 *.flac *.wav *.ogg *.m4a *.aac *.wma);;"
            "All Files (*)"
        )

        if file_path:
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
            "Audio Files (*.mp3 *.flac *.wav *.ogg *.m4a *.aac *.wma);;"
            "All Files (*)"
        )

        if file_paths:
            for file_path in file_paths:
                self.playlist.add_media_file(file_path)
                self._register_library_path(file_path)
            self.load_media(file_paths[0])
            self.playlist.setCurrentRow(0)
            self.refresh_home_grid()

    def open_folder(self):
        """Open folder dialog and load all media files from folder"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Open Media Folder", ""
        )

        if folder_path:
            # Find all media files in the folder
            media_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.is_supported_media_file(file_path):
                        media_files.append(file_path)

            if media_files:
                media_files.sort()
                for file_path in media_files:
                    self.playlist.add_media_file(file_path)
                    self._register_library_path(file_path)
                self.load_media(media_files[0])
                self.playlist.setCurrentRow(0)
                self.refresh_home_grid()
            else:
                QMessageBox.information(self, "No Media Files",
                                      "No supported media files found in the selected folder.")

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
                url = QUrl.fromLocalFile(file_path)

            if hasattr(self, "engine"):
                self.engine.set_source(file_path)
            else:
                self.media_player.setSource(url)
            self.app_state.last_file = file_path
            self._register_library_path(file_path)
            self.refresh_home_grid()

            self.show_logo(False)
            self.show_shell_page("stage")

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
                engine_name = self.engine.backend_name if hasattr(self, "engine") else "qt"
                label = "libmpv (HW)" if engine_name == "mpv" else "Qt Multimedia"
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

            # Try to load subtitles
            subtitle_path = os.path.splitext(file_path)[0] + ".srt"
            if os.path.exists(subtitle_path):
                self.subtitle_manager.load_subtitles(subtitle_path)
                self.status_bar.showMessage(f"Loaded: {filename} + Subtitles ({file_size_mb:.1f}MB, {file_ext})")

            # Enrich metadata (network) without blocking the UI long-term
            QTimer.singleShot(50, lambda p=file_path: self._enrich_current_media(p))

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load media file:\n{str(e)}")
            self.status_bar.showMessage(f"Error loading: {os.path.basename(file_path)}")

    def _enrich_current_media(self, file_path: str):
        """Run metadata enrichment and refresh Now Playing / Media Info fields."""
        if not file_path or not os.path.isfile(file_path):
            return
        if file_path in self._meta_cache:
            self._apply_enriched_metadata(self._meta_cache[file_path])
            return

        cover_dest = self.thumb_cache.path_for(file_path + ".cover")
        worker = MetadataEnrichWorker(file_path, cover_dest, self)
        self._enrich_thread = worker

        def _on_done(meta: MediaMetadata):
            if not meta or meta.path != getattr(self.app_state, "last_file", ""):
                if meta and meta.path:
                    self._meta_cache[meta.path] = meta
                return
            self._meta_cache[meta.path] = meta
            self._apply_enriched_metadata(meta)

        worker.finished_meta.connect(_on_done)
        worker.start()

    def _apply_enriched_metadata(self, meta: MediaMetadata):
        if not meta:
            return
        title = meta.display_title()
        subtitle = meta.display_subtitle()
        cover = meta.cover_path or self._thumb_map.get(meta.path) or get_thumbnail_path(meta.path)
        if cover:
            self._thumb_map[meta.path] = cover
        if hasattr(self, "now_playing"):
            engine_name = self.engine.backend_name if hasattr(self, "engine") else "qt"
            label = "libmpv (HW)" if engine_name == "mpv" else "Qt Multimedia"
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
        self.status_bar.showMessage(
            f"Metadata ({meta.source}): {title}" + (f" — {subtitle}" if subtitle else ""),
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
        if hasattr(self, "engine") and self.app_state.last_file:
            QTimer.singleShot(200, self._start_playback_with_gain)
        elif self.media_player.source().isValid():
            QTimer.singleShot(200, self._start_playback_with_gain)

    def _start_playback_with_gain(self):
        """Start playback then re-apply volume (Pulse sink-input appears after play)."""
        if hasattr(self, "engine"):
            self.engine.play()
        else:
            self.media_player.play()
        # Re-apply logical volume once the audio stream exists
        QTimer.singleShot(400, self._apply_output_gain_from_state)
        QTimer.singleShot(1200, self._apply_output_gain_from_state)
        if self._preview_timer and not self._preview_timer.isActive():
            self._preview_timer.start()

    def previous_media(self):
        """Go to previous media file in playlist"""
        if hasattr(self, 'playlist') and self.playlist:
            current_file = self.app_state.last_file
            if current_file:
                # Find current file index in playlist
                current_index = self.playlist.find_file_index(current_file)
                if current_index is not None and current_index > 0:
                    # Load previous file
                    prev_file = self.playlist.get_file_at_index(current_index - 1)
                    if prev_file:
                        # Update playlist selection
                        self.playlist.setCurrentRow(current_index - 1)
                        self.load_media(prev_file)
                        self.status_bar.showMessage(f"Previous: {os.path.basename(prev_file)}")
                    else:
                        self.status_bar.showMessage("No previous file in playlist")
                else:
                    self.status_bar.showMessage("Already at first file in playlist")
            else:
                self.status_bar.showMessage("No current file loaded")
        else:
            self.status_bar.showMessage("No playlist available")

    def next_media(self):
        """Go to next media file in playlist"""
        if hasattr(self, 'playlist') and self.playlist:
            current_file = self.app_state.last_file
            if current_file:
                # Find current file index in playlist
                current_index = self.playlist.find_file_index(current_file)
                if current_index is not None and current_index < self.playlist.count() - 1:
                    # Load next file
                    next_file = self.playlist.get_file_at_index(current_index + 1)
                    if next_file:
                        # Update playlist selection
                        self.playlist.setCurrentRow(current_index + 1)
                        self.load_media(next_file)
                        self.status_bar.showMessage(f"Next: {os.path.basename(next_file)}")
                    else:
                        self.status_bar.showMessage("No next file in playlist")
                else:
                    self.status_bar.showMessage("Already at last file in playlist")
            else:
                self.status_bar.showMessage("No current file loaded")
        else:
            self.status_bar.showMessage("No playlist available")

    def play_selected_item(self):
        """Play the currently selected playlist item"""
        file_path = self.playlist.get_current_file()
        if file_path:
            self.load_media(file_path)
            self.toggle_playback()

    def toggle_playback(self):
        """Toggle play/pause"""
        if hasattr(self, "engine"):
            self.engine.toggle()
            return
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def stop_playback(self):
        """Stop playback"""
        if hasattr(self, "engine"):
            self.engine.stop()
            return
        self.media_player.stop()

    def toggle_mute(self):
        """Toggle mute"""
        if hasattr(self, "engine"):
            muted = not self.engine.is_muted()
            self.engine.set_muted(muted)
            self.controls.btn_mute.setText("🔇" if muted else "🔊")
            return
        self.audio_output.setMuted(not self.audio_output.isMuted())
        self.controls.btn_mute.setText("🔇" if self.audio_output.isMuted() else "🔊")

    def _apply_output_gain_from_state(self):
        """Apply persisted 0..200 user volume with real gain (mpv / Pulse / Qt)."""
        if hasattr(self, "engine"):
            self.engine.set_volume_percent(int(self.app_state.volume))
            return
        gain = max(0.0, min(1.0, float(self.app_state.volume) / 100.0))
        self.audio_output.setVolume(gain)

    def set_volume(self, volume):
        """Set volume (0-200) using linear gain; Media Info reports the same %."""
        volume = max(0, min(200, int(volume)))
        gain = volume / 100.0

        # Persist logical volume so keyboard/slider/Media Info stay in sync.
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

        if volume > 100:
            self.status_bar.showMessage(
                f"Volume: {volume}% (boost active — clipping may occur)",
                2500,
            )

    def adjust_volume(self, delta):
        """Adjust volume by delta"""
        # Use the logical app volume so 101-200% amplification is preserved.
        current_volume = int(self.app_state.volume)
        new_volume = max(0, min(200, current_volume + delta))
        self.controls.volume_slider.setValue(int(new_volume))
        self.set_volume(int(new_volume))

    def seek_to_position(self, position):
        """Seek to position (0.0-1.0)"""
        if hasattr(self, "engine"):
            dur = self.engine.duration()
            if dur > 0:
                self.engine.set_position(int(position * dur))
            return
        if self.media_player.duration() > 0:
            pos = int(position * self.media_player.duration())
            self.media_player.setPosition(pos)

    def seek_relative(self, seconds):
        """Seek relative to current position"""
        if hasattr(self, "engine"):
            self.engine.seek_relative(seconds)
            return
        current_pos = self.media_player.position()
        new_pos = max(0, current_pos + seconds * 1000)
        self.media_player.setPosition(new_pos)

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
        """Toggle playlist visibility"""
        if not hasattr(self, 'playlist_dock'):
            return
        if self.playlist_visible:
            self.playlist_dock.hide()
            self.playlist_visible = False
        else:
            self.playlist_dock.show()
            self.playlist_visible = True

    def hide_playlist(self):
        """Hide playlist (only in fullscreen)"""
        if not hasattr(self, 'playlist_dock'):
            return
        if self.isFullScreen() and self.playlist_visible:
            self.playlist_dock.hide()
            self.playlist_visible = False

    def show_playlist(self):
        """Show playlist"""
        if not hasattr(self, 'playlist_dock'):
            return
        if not self.playlist_visible:
            self.playlist_dock.show()
            self.playlist_visible = True

    def show_timeline_preview(self, show):
        """Show or hide timeline preview"""
        if show and self.media_player.duration() > 0:
            self.timeline_preview.show()
        else:
            self.timeline_preview.hide()

    def update_timeline_preview(self, position):
        """Update timeline preview with time information"""
        if self.media_player.duration() > 0:
            # Calculate time at this position
            time_ms = int(position * self.media_player.duration())
            total_ms = self.media_player.duration()

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

            # Check if mouse is near right edge for playlist
            mouse_x = event.position().x()
            window_width = self.width()
            if mouse_x > window_width - 50:  # Within 50px of right edge
                self.show_playlist()
                self.playlist_timer.start(2000)  # Hide after 2 seconds
            else:
                self.playlist_timer.start(2000)  # Start hide timer
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
        """Handle playback state changes"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.controls.btn_play.setText("⏸")
            self.status_bar.showMessage("Playing")
            # Hide logo when playing
            self.show_logo(False)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.controls.btn_play.setText("▶")
            self.status_bar.showMessage("Paused")
            # Show logo when paused
            self.show_logo(True)
        else:
            self.controls.btn_play.setText("▶")
            self.status_bar.showMessage("Stopped")
            # Show logo when stopped
            self.show_logo(True)

        # Auto-play next item when current media ends
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.auto_play_next()

    def auto_play_next(self):
        """Auto-play next item in playlist when current media ends"""
        if hasattr(self, 'playlist') and self.playlist:
            current_file = self.app_state.last_file
            if current_file:
                # Find current file index in playlist
                current_index = self.playlist.find_file_index(current_file)
                if current_index is not None and current_index < self.playlist.count() - 1:
                    # Load next file
                    next_file = self.playlist.get_file_at_index(current_index + 1)
                    if next_file:
                        self.load_media(next_file)
                        self.status_bar.showMessage(f"Auto-playing: {os.path.basename(next_file)}")
                        # Auto-start playback
                        QTimer.singleShot(100, self.media_player.play)

    def media_error(self, error, error_string):
        """Handle media errors"""
        # Only show critical errors to user, suppress common warnings
        if error_string and "pts == AV_NOPTS_VALUE" not in error_string:
            if "Unknown property transform" not in error_string:
                QMessageBox.warning(self, "Media Error", f"Error: {error_string}")
                self.status_bar.showMessage(f"Error: {error_string}")
            else:
                # Suppress transform warnings
                pass
        else:
            # Suppress pts warnings as they're common and not critical
            pass

    def update_ui(self):
        """Update UI elements"""
        duration = self.engine.duration() if hasattr(self, "engine") else self.media_player.duration()
        if duration > 0:
            current_pos = self.engine.position() if hasattr(self, "engine") else self.media_player.position()
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

            if hasattr(self, "engine"):
                duration = self.engine.duration()
                position = self.engine.position()
                state = "Playing" if self.engine.is_playing() else (
                    "Paused" if self.engine.backend_name else "Stopped"
                )
                if self.engine.backend_name == "qt":
                    state = self.media_player.playbackState().name
                muted = self.engine.is_muted()
                engine_label = "libmpv" if self.engine.backend_name == "mpv" else "Qt Multimedia"
            else:
                duration = self.media_player.duration()
                position = self.media_player.position()
                state = self.media_player.playbackState().name
                muted = self.audio_output.isMuted()
                engine_label = "Qt Multimedia"

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
        """Show about dialog"""
        QMessageBox.about(self, "About VoxPlayer",
                         "VoxPlayer — modern desktop media shell\n\n"
                         "PyQt6 UI + optional libmpv native decode\n"
                         "Local library, queue, torrent streaming\n\n"
                         f"Version {self.current_version}")

    def closeEvent(self, event):
        """Handle application close"""
        self.app_state.window_geometry = self.saveGeometry()
        self.settings.save_state(self.app_state)
        if hasattr(self, "engine"):
            self.engine.shutdown()
        event.accept()

def main():
    # Suppress verbose console output
    os.environ['QT_LOGGING_RULES'] = 'qt.multimedia.ffmpeg.debug=false'

    app = QApplication(sys.argv)
    app.setApplicationName("VoxPlayer")
    app.setApplicationVersion("1.1.0")

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

    window = VoxPlayerMainWindow(file_to_open)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()


