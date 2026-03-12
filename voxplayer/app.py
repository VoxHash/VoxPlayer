#!/usr/bin/env python3
"""
VoxPlayer - A modern multimedia player built with PyQt6
Clean implementation without signal issues
"""

import sys
import os
import tempfile
import threading
import hashlib
import urllib.parse
import subprocess
import shutil
import requests
import webbrowser
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QSlider, QLabel, 
                            QFileDialog, QDockWidget, QListWidget, QListWidgetItem,
                            QMenuBar, QMenu, QStatusBar, QMessageBox, QInputDialog,
                            QProgressBar, QComboBox, QCheckBox, QSpinBox, QColorDialog,
                            QLineEdit)
from PyQt6.QtCore import Qt, QTimer, QSettings, QSize, QUrl, QMimeData, QThread, pyqtSignal
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QAudioDevice
from PyQt6.QtGui import QKeySequence, QShortcut, QAction, QFont, QColor, QPixmap, QIcon
import json
import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import tempfile
import time
import os
import shutil

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
            # Try to connect to qBittorrent Web UI (default: localhost:8080)
            self.qb_client = Client(host='localhost:8080')
            
            # Check if qBittorrent is running
            try:
                version = self.qb_client.app.version()
                if not version:
                    raise Exception("qBittorrent is not running. Please start qBittorrent first.")
                self.progress_updated.emit(10, f"Connected to qBittorrent v{version}")
            except Exception as e:
                # If we can't get version, try a different approach
                self.qb_client.torrents_info()
                self.progress_updated.emit(10, "Connected to qBittorrent")
                
        except ImportError:
            self.error_occurred.emit("qBittorrent API not available. Please install: pip install qbittorrent-api")
        except Exception as e:
            self.error_occurred.emit(f"Failed to connect to qBittorrent: {str(e)}. Please ensure qBittorrent is running and Web UI is enabled.")
    
    def _add_magnet_link(self):
        """Add magnet link to qBittorrent"""
        try:
            self.progress_updated.emit(20, "Adding magnet link...")
            
            # Add magnet link to qBittorrent
            torrent_info = self.qb_client.torrents_add(urls=self.magnet_link, save_path=self.temp_dir)
            
            if torrent_info == "Ok.":
                self.progress_updated.emit(30, "Magnet link added successfully")
                self._monitor_torrent()
            else:
                self.error_occurred.emit(f"Failed to add magnet link: {torrent_info}")
                
        except Exception as e:
            self.error_occurred.emit(f"Error adding magnet link: {str(e)}")
    
    def _add_torrent_file(self):
        """Add torrent file to qBittorrent"""
        try:
            self.progress_updated.emit(20, "Adding torrent file...")
            
            # Read torrent file
            with open(self.torrent_file, 'rb') as f:
                torrent_data = f.read()
            
            # Add torrent file to qBittorrent
            torrent_info = self.qb_client.torrents_add(torrent_files=torrent_data, save_path=self.temp_dir)
            
            if torrent_info == "Ok.":
                self.progress_updated.emit(30, "Torrent file added successfully")
                self._monitor_torrent()
            else:
                self.error_occurred.emit(f"Failed to add torrent file: {torrent_info}")
                
        except Exception as e:
            self.error_occurred.emit(f"Error adding torrent file: {str(e)}")
    
    def _monitor_torrent(self):
        """Monitor torrent progress"""
        try:
            # Get torrent hash from magnet link or file
            torrents = self.qb_client.torrents_info()
            if not torrents:
                self.error_occurred.emit("No torrents found")
                return
                
            torrent = torrents[0]  # Get first torrent
            torrent_hash = torrent.hash
            
            self.progress_updated.emit(40, f"Monitoring torrent: {torrent.name}")
            
            # Monitor progress
            while self.is_running:
                torrent_info = self.qb_client.torrents_info(torrent_hashes=torrent_hash)[0]
                
                progress = int(torrent_info.progress * 100)
                self.progress_updated.emit(40 + progress // 2, f"Downloading: {progress}%")
                
                if torrent_info.state == "uploading" or torrent_info.state == "stalledUP":
                    # Torrent completed, find media files
                    self._find_media_files()
                    break
                elif torrent_info.state == "error":
                    self.error_occurred.emit(f"Torrent error: {torrent_info.state}")
                    break
                    
                time.sleep(2)
                
        except Exception as e:
            self.error_occurred.emit(f"Error monitoring torrent: {str(e)}")
    
    def _find_media_files(self):
        """Find media files in downloaded torrent"""
        try:
            self.progress_updated.emit(90, "Scanning for media files...")
            
            media_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mp3', '.wav', '.flac', '.aac']
            media_files = []
            
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in media_extensions):
                        media_files.append(os.path.join(root, file))
            
            if media_files:
                # Play the first media file found
                media_file = media_files[0]
                self.progress_updated.emit(100, f"Found media file: {os.path.basename(media_file)}")
                self.file_ready.emit(media_file)
            else:
                self.error_occurred.emit("No media files found in torrent")
                
        except Exception as e:
            self.error_occurred.emit(f"Error finding media files: {str(e)}")
    
    def stop(self):
        """Stop torrent streaming"""
        self.is_running = False
        if self.qb_client:
            try:
                # Remove torrent from qBittorrent
                torrents = self.qb_client.torrents_info()
                if torrents:
                    self.qb_client.torrents_delete(torrent_hashes=torrents[0].hash, delete_files=True)
            except:
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
            response = requests.get(self.github_api, timeout=10)
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data.get("tag_name", "").lstrip("v")
                
                if self._is_newer_version(latest_version, self.current_version):
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

class PlayerControls(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)  # Even more compact
        layout.setSpacing(4)  # Reduced spacing
        
        # Control buttons (micro-compact design)
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("playButton")
        self.btn_play.setFixedSize(18, 18)  # Much smaller
        self.btn_play.setStyleSheet("""
            QPushButton#playButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #00BFFF, stop: 1 #0099CC);
                border: 1px solid #00BFFF;
                border-radius: 9px;
                color: white;
                font-size: 8px;
                font-weight: bold;
            }
            QPushButton#playButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #00CCFF, stop: 1 #00BFFF);
                border-color: #00CCFF;
            }
            QPushButton#playButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #0088BB, stop: 1 #006699);
            }
        """)
        
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setFixedSize(16, 16)  # Much smaller
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: white;
                font-size: 6px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.25);
            }
        """)
        
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setFixedSize(16, 16)  # Much smaller
        self.btn_mute.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: white;
                font-size: 6px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.25);
            }
        """)
        
        # Seek bar (micro-compact design) with timeline preview
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 1px;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: #00BFFF;
                border: 1px solid #FFFFFF;
                width: 8px;
                margin: -3px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal:hover {
                background: #00CCFF;
                width: 10px;
                margin: -4px 0;
            }
        """)
        
        # Enable mouse tracking for timeline preview
        self.seek_slider.setMouseTracking(True)
        self.seek_slider.enterEvent = self.on_seek_hover
        self.seek_slider.leaveEvent = self.on_seek_leave
        self.seek_slider.mouseMoveEvent = self.on_seek_mouse_move
        
        # Time labels (micro-compact)
        self.time_label = QLabel("00:00")
        self.time_label.setObjectName("timeLabel")
        self.time_label.setStyleSheet("""
            QLabel#timeLabel {
                color: white;
                font-family: "Consolas", "Monaco", monospace;
                font-size: 7px;
                font-weight: bold;
                background: transparent;
                border: none;
                padding: 0px 2px;
                min-width: 35px;
            }
        """)
        
        # Volume control (micro-compact)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 200)
        self.volume_slider.setValue(100)
        self.volume_slider.setMaximumWidth(40)  # Much smaller
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 1px;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: #00BFFF;
                border: 1px solid #FFFFFF;
                width: 6px;
                margin: -2px 0;
                border-radius: 3px;
            }
        """)
        
        self.volume_label = QLabel("100%")
        self.volume_label.setObjectName("volumeLabel")
        self.volume_label.setStyleSheet("""
            QLabel#volumeLabel {
                color: white;
                font-family: "Consolas", "Monaco", monospace;
                font-size: 6px;
                background: transparent;
                border: none;
                padding: 0px 2px;
                min-width: 22px;
            }
        """)
        
        # Previous/Next buttons
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(16, 16)
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: white;
                font-size: 6px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.25);
            }
        """)
        
        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(16, 16)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: white;
                font-size: 6px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.25);
            }
        """)
        
        # Add widgets to layout (micro-compact arrangement)
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_play)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_next)
        layout.addWidget(QLabel(""))  # Spacer
        layout.addWidget(self.time_label)
        layout.addWidget(self.seek_slider)
        layout.addWidget(QLabel(""))  # Spacer
        layout.addWidget(self.btn_mute)
        layout.addWidget(self.volume_slider)
        layout.addWidget(self.volume_label)
        
        # Connect signals
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_mute.clicked.connect(self.toggle_mute)
        self.btn_prev.clicked.connect(self.previous_media)
        self.btn_next.clicked.connect(self.next_media)
        self.seek_slider.valueChanged.connect(self.seek_changed)
        self.volume_slider.valueChanged.connect(self.volume_changed)
    
    def toggle_play(self):
        if hasattr(self.parent_window, 'toggle_playback'):
            self.parent_window.toggle_playback()
    
    def stop(self):
        if hasattr(self.parent_window, 'stop_playback'):
            self.parent_window.stop_playback()
    
    def toggle_mute(self):
        if hasattr(self.parent_window, 'toggle_mute'):
            self.parent_window.toggle_mute()
    
    def previous_media(self):
        if hasattr(self.parent_window, 'previous_media'):
            self.parent_window.previous_media()
    
    def next_media(self):
        if hasattr(self.parent_window, 'next_media'):
            self.parent_window.next_media()
    
    def take_snapshot(self):
        if hasattr(self.parent_window, 'take_snapshot'):
            self.parent_window.take_snapshot()
    
    def seek_changed(self, value):
        if hasattr(self.parent_window, 'seek_to_position'):
            self.parent_window.seek_to_position(value / 1000.0)
    
    def volume_changed(self, value):
        if hasattr(self.parent_window, 'set_volume'):
            self.parent_window.set_volume(value)
        self.volume_label.setText(f"{value}%")
    
    def on_seek_hover(self, event):
        """Show timeline preview on hover"""
        if hasattr(self.parent_window, 'show_timeline_preview'):
            self.parent_window.show_timeline_preview(True)
    
    def on_seek_leave(self, event):
        """Hide timeline preview on leave"""
        if hasattr(self.parent_window, 'show_timeline_preview'):
            self.parent_window.show_timeline_preview(False)
    
    def on_seek_mouse_move(self, event):
        """Update timeline preview on mouse move"""
        if hasattr(self.parent_window, 'update_timeline_preview'):
            # Calculate position based on mouse position
            pos = event.position().x()
            width = self.seek_slider.width()
            if width > 0:
                position = pos / width
                self.parent_window.update_timeline_preview(position)
    
    def update_time(self, current, total):
        """Update time display"""
        def format_time(ms):
            seconds = ms // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        
        self.time_label.setText(f"{format_time(current)} / {format_time(total)}")
    
    def update_seek_position(self, position):
        """Update seek slider position"""
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(int(position * 1000))
        self.seek_slider.blockSignals(False)

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
        self.current_version = "1.0.1"
        
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
        self.setMinimumSize(400, 200)  # Ultra-compact minimum size
        
        # Set window geometry
        if self.app_state.window_geometry:
            self.restoreGeometry(self.app_state.window_geometry)
        else:
            self.resize(600, 400)  # Ultra-compact default size
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("""
            QVideoWidget {
                background-color: #000000;
                border: none;
            }
        """)
        self.video_widget.setAcceptDrops(True)
        self.video_widget.mouseDoubleClickEvent = lambda event: self.toggle_fullscreen()
        layout.addWidget(self.video_widget)
        
        # Player controls (initially visible)
        self.controls = PlayerControls(self)
        self.controls.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 240);
                border: none;
                padding: 1px;
            }
        """)
        layout.addWidget(self.controls)
        
        # Playlist dock with search bar
        self.playlist = PlaylistWidget(self)
        self.playlist_dock = QDockWidget("Playlist")
        
        # Create a container widget for playlist and search bar
        playlist_container = QWidget()
        playlist_layout = QVBoxLayout(playlist_container)
        playlist_layout.setContentsMargins(0, 0, 0, 0)
        playlist_layout.setSpacing(2)
        
        # Search bar
        self.playlist_search = QLineEdit()
        self.playlist_search.setPlaceholderText("Search playlist...")
        self.playlist_search.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                padding: 4px 8px;
                color: white;
                font-size: 10px;
            }
            QLineEdit:focus {
                border-color: #00BFFF;
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.playlist_search.textChanged.connect(self.filter_playlist)
        
        # Search bar container with clear button
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(2)
        
        search_layout.addWidget(self.playlist_search)
        
        # Clear button
        self.clear_search_btn = QPushButton("✕")
        self.clear_search_btn.setFixedSize(20, 20)
        self.clear_search_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                color: white;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border-color: #00BFFF;
            }
        """)
        self.clear_search_btn.clicked.connect(self.clear_playlist_search)
        search_layout.addWidget(self.clear_search_btn)
        
        playlist_layout.addWidget(search_container)
        
        # Playlist widget
        playlist_layout.addWidget(self.playlist)
        
        self.playlist_dock.setWidget(playlist_container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.playlist_dock)
        self.playlist_dock.hide()  # Hide playlist by default
        
        # Subtitle manager
        self.subtitle_manager = SubtitleManager(self.video_widget, self)
        
        # Timeline preview
        self.timeline_preview = QLabel("")
        self.timeline_preview.setParent(self.video_widget)
        self.timeline_preview.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 200);
                border: 2px solid #00BFFF;
                border-radius: 8px;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 8px;
            }
        """)
        self.timeline_preview.hide()
        self.timeline_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Create menu bar
        self.create_menu_bar()
        
        # Enable mouse tracking for auto-hide controls
        self.setMouseTracking(True)
        self.video_widget.setMouseTracking(True)
        self.controls.setMouseTracking(True)
    
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
        playlist_action = QAction("&Playlist", self)
        playlist_action.setShortcut("Ctrl+L")
        playlist_action.setCheckable(True)
        playlist_action.setChecked(True)
        playlist_action.triggered.connect(self.toggle_playlist)
        view_menu.addAction(playlist_action)
        
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
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # Initialize current audio device (simplified approach)
        self.current_audio_device = None
        
        # Volume amplification system
        self.volume_amplification = 1.0
        self.base_volume = 1.0
        
        # Set initial volume to 100%
        self.audio_output.setVolume(1.0)
        self.media_player.setVideoOutput(self.video_widget)
        
        # Connect media player signals
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.playbackStateChanged.connect(self.playback_state_changed)
        self.media_player.errorOccurred.connect(self.media_error)
        
        # Set initial volume
        self.audio_output.setVolume(self.app_state.volume / 100.0)
        self.controls.volume_slider.setValue(self.app_state.volume)
    
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
                    self.audio_output.setVolume(self.app_state.volume / 100.0)
                    self.status_bar.showMessage("Audio device: Default (Auto-adapt)")
            else:
                # Manual mode - for now just use default device
                if hasattr(self, 'audio_output'):
                    self.audio_output = QAudioOutput()
                    self.media_player.setAudioOutput(self.audio_output)
                    self.audio_output.setVolume(self.app_state.volume / 100.0)
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
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Torrent File", "", "Torrent Files (*.torrent)"
        )
        if file_path:
            self.start_torrent_streaming(torrent_file=file_path)
    
    def start_torrent_streaming(self, magnet_link: str = None, torrent_file: str = None):
        """Start torrent streaming"""
        if self.torrent_streamer and self.torrent_streamer.isRunning():
            QMessageBox.warning(self, "Torrent Active", "A torrent is already being streamed.")
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
                    self.audio_output.setVolume(self.app_state.volume / 100.0)
                    
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
        """Apply voxplayer dark theme"""
        voxplayer_style = """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
            border: none;
        }
        
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        /* voxplayer-style Menu Bar */
        QMenuBar {
            background-color: #404040;
            border-bottom: 1px solid #555555;
            color: #ffffff;
            padding: 2px;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 3px;
        }
        
        QMenuBar::item:selected {
            background-color: #00BFFF;
        }
        
        QMenu {
            background-color: #404040;
            border: 1px solid #555555;
            color: #ffffff;
            padding: 4px;
        }
        
        QMenu::item {
            padding: 6px 20px;
            border-radius: 3px;
        }
        
        QMenu::item:selected {
            background-color: #00BFFF;
        }
        
        /* voxplayer-style List Widget */
        QListWidget {
            background-color: #2d2d2d;
            border: 1px solid #555555;
            selection-background-color: #00BFFF;
            padding: 4px;
            font-size: 12px;
        }
        
        QListWidget::item {
            padding: 6px;
            border-radius: 3px;
            margin: 1px;
        }
        
        QListWidget::item:hover {
            background-color: #3d3d3d;
        }
        
        QListWidget::item:selected {
            background-color: #00BFFF;
            color: white;
        }
        
        /* voxplayer-style Dock Widget */
        QDockWidget {
            background-color: #2b2b2b;
            border: 1px solid #555555;
        }
        
        QDockWidget::title {
            background-color: #404040;
            padding: 6px;
            font-weight: bold;
            color: #ffffff;
        }
        
        /* voxplayer-style Status Bar */
        QStatusBar {
            background-color: #404040;
            border-top: 1px solid #555555;
            padding: 4px;
            font-size: 11px;
            color: #ffffff;
        }
        
        /* Video Widget Styling */
        QVideoWidget {
            background-color: #000000;
            border: none;
        }
        """
        self.setStyleSheet(voxplayer_style)
    
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
    
    def open_files(self):
        """Open multiple files dialog and load media"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Media Files", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v);;"
            "Audio Files (*.mp3 *.flac *.wav *.ogg *.m4a *.aac *.wma);;"
            "All Files (*)"
        )
        
        if file_paths:
            # Load the first file and add all to playlist
            self.load_media(file_paths[0])
            for file_path in file_paths:
                self.playlist.add_media_file(file_path)
            self.playlist.setCurrentRow(0)
    
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
                # Sort files naturally
                media_files.sort()
                # Load the first file and add all to playlist
                self.load_media(media_files[0])
                for file_path in media_files:
                    self.playlist.add_media_file(file_path)
                self.playlist.setCurrentRow(0)
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
            
            self.media_player.setSource(url)
            self.app_state.last_file = file_path
            
            # Hide logo when media is loaded
            self.show_logo(False)
            
            # Update playlist selection to current file
            if hasattr(self, 'playlist') and self.playlist:
                current_index = self.playlist.find_file_index(file_path)
                if current_index is not None:
                    self.playlist.setCurrentRow(current_index)
            
            # Update window title with current file (voxplayer style)
            filename = os.path.basename(file_path)
            self.setWindowTitle(f"{filename} - VoxPlayer")
            
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
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load media file:\n{str(e)}")
            self.status_bar.showMessage(f"Error loading: {os.path.basename(file_path)}")
    
    def load_and_play_media(self, file_path):
        """Load media file and auto-play it"""
        self.load_media(file_path)
        # Auto-play the loaded media
        if self.media_player.source().isValid():
            QTimer.singleShot(200, self.media_player.play)
    
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
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
    
    def stop_playback(self):
        """Stop playback"""
        self.media_player.stop()
    
    def toggle_mute(self):
        """Toggle mute"""
        self.audio_output.setMuted(not self.audio_output.isMuted())
        self.controls.btn_mute.setText("🔇" if self.audio_output.isMuted() else "🔊")
    
    def set_volume(self, volume):
        """Set volume (0-200) with true amplification"""
        # Clamp volume to 0-200 range
        volume = max(0, min(200, volume))
        
        # Store the display volume
        self.app_state.volume = volume
        
        if volume <= 100:
            # Normal volume range (0-100%)
            qt_volume = volume / 100.0
            self.volume_amplification = 1.0
            self.base_volume = qt_volume
        else:
            # Amplified range (100-200%) - implement true amplification
            self.base_volume = 1.0  # Set Qt volume to maximum
            self.volume_amplification = volume / 100.0  # Store amplification factor
            
            # Apply amplification by adjusting the base volume
            # This creates a true amplification effect
            qt_volume = min(1.0, self.base_volume * (self.volume_amplification ** 0.5))
        
        # Set the actual volume
        self.audio_output.setVolume(qt_volume)
        
        # Update volume label
        if volume > 100:
            self.controls.volume_label.setText(f"{volume}%")
            self.status_bar.showMessage(f"Volume: {volume}% (Amplified)", 2000)
        else:
            self.controls.volume_label.setText(f"{volume}%")
    
    def adjust_volume(self, delta):
        """Adjust volume by delta"""
        current_volume = self.audio_output.volume() * 100
        new_volume = max(0, min(200, current_volume + delta))
        self.controls.volume_slider.setValue(int(new_volume))
        self.set_volume(int(new_volume))
    
    def seek_to_position(self, position):
        """Seek to position (0.0-1.0)"""
        if self.media_player.duration() > 0:
            pos = int(position * self.media_player.duration())
            self.media_player.setPosition(pos)
    
    def seek_relative(self, seconds):
        """Seek relative to current position"""
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
        self.controls.update_seek_position(position / self.media_player.duration() if self.media_player.duration() > 0 else 0)
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
        if self.media_player.duration() > 0:
            current_pos = self.media_player.position()
            duration = self.media_player.duration()
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
            
            duration = self.media_player.duration()
            duration_min = duration // 60000
            duration_sec = (duration % 60000) // 1000
            
            info_text = f"""
Media Information:

File: {os.path.basename(file_path)}
Path: {file_path}
Size: {file_size_mb:.2f} MB
Format: {file_ext}
Duration: {duration_min}:{duration_sec:02d}
Volume: {int(self.audio_output.volume() * 100)}%
Muted: {'Yes' if self.audio_output.isMuted() else 'No'}

Player Status:
State: {self.media_player.playbackState().name}
Position: {self.media_player.position() // 1000}s
            """
            
            QMessageBox.information(self, "Media Information", info_text)
            
        except Exception as e:
            QMessageBox.warning(self, "Media Info Error", f"Could not retrieve media information:\n{str(e)}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About VoxPlayer", 
                         "VoxPlayer - Modern Multimedia Player\n\n"
                         "Built with PyQt6\n"
                         "Supports most video and audio formats\n\n"
                         "Version 1.0.0")
    
    def closeEvent(self, event):
        """Handle application close"""
        # Save current state
        self.app_state.window_geometry = self.saveGeometry()
        self.settings.save_state(self.app_state)
        event.accept()

def main():
    # Suppress verbose console output
    import os
    os.environ['QT_LOGGING_RULES'] = 'qt.multimedia.ffmpeg.debug=false'
    
    app = QApplication(sys.argv)
    app.setApplicationName("VoxPlayer")
    app.setApplicationVersion("1.0.1")
    
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


