"""
Modern VoxPlayer shell: left library rail, center home/stage, now-playing,
and bottom transport — layout patterns adapted for a unique Vox identity.
"""

from __future__ import annotations

import os
from typing import Callable, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSlider,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QFrame,
    QGridLayout,
    QSizePolicy,
    QStackedWidget,
    QSpacerItem,
)

from ..theme import COLORS


class MediaCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(
        self,
        title: str,
        subtitle: str,
        path: str,
        parent=None,
        thumbnail_path: Optional[str] = None,
    ):
        super().__init__(parent)
        self.path = path
        self.setObjectName("MediaCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(160, 190)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.art = QLabel()
        self.art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art.setFixedSize(140, 120)
        self.art.setStyleSheet(
            f"background: {COLORS['bg_input']}; border-radius: 8px; color: {COLORS['accent']}; font-size: 28px;"
        )
        ext = os.path.splitext(path)[1].lower()
        if thumbnail_path and os.path.isfile(thumbnail_path):
            self.set_thumbnail(thumbnail_path)
        else:
            self.art.setText("▶" if ext in {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"} else "♪")
        layout.addWidget(self.art)

        name = QLabel(title)
        name.setWordWrap(True)
        name.setObjectName("MetaPrimary")
        name.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px; font-weight: 600;")
        layout.addWidget(name)

        sub = QLabel(subtitle)
        sub.setObjectName("MetaMuted")
        sub.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(sub)

    def set_thumbnail(self, thumbnail_path: str) -> None:
        if not thumbnail_path or not os.path.isfile(thumbnail_path):
            return
        pix = QPixmap(thumbnail_path)
        if pix.isNull():
            return
        self.art.setText("")
        self.art.setPixmap(
            pix.scaled(
                140,
                120,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.path)
        super().mousePressEvent(event)


class LeftRail(QWidget):
    home_requested = pyqtSignal()
    library_requested = pyqtSignal()
    queue_requested = pyqtSignal()
    open_file_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()
    torrent_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LeftRail")
        self.setFixedWidth(72)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(6)

        brand = QLabel("VX")
        brand.setObjectName("BrandMark")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(brand)
        layout.addSpacing(8)

        self.btn_home = self._rail_btn("⌂", "Home")
        self.btn_library = self._rail_btn("▤", "Library")
        self.btn_queue = self._rail_btn("☰", "Queue")
        self.btn_open = self._rail_btn("+", "Open file")
        self.btn_folder = self._rail_btn("📁", "Open folder")
        self.btn_torrent = self._rail_btn("↯", "Torrent")

        self.btn_home.clicked.connect(self.home_requested.emit)
        self.btn_library.clicked.connect(self.library_requested.emit)
        self.btn_queue.clicked.connect(self.queue_requested.emit)
        self.btn_open.clicked.connect(self.open_file_requested.emit)
        self.btn_folder.clicked.connect(self.open_folder_requested.emit)
        self.btn_torrent.clicked.connect(self.torrent_requested.emit)

        for b in (
            self.btn_home,
            self.btn_library,
            self.btn_queue,
            self.btn_open,
            self.btn_folder,
            self.btn_torrent,
        ):
            layout.addWidget(b)

        layout.addStretch(1)
        self.set_active("home")

    def _rail_btn(self, glyph: str, tip: str) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setObjectName("RailButton")
        btn.setToolTip(tip)
        btn.setFixedSize(56, 44)
        btn.setProperty("active", "false")
        return btn

    def set_active(self, which: str) -> None:
        mapping = {
            "home": self.btn_home,
            "library": self.btn_library,
            "queue": self.btn_queue,
        }
        for key, btn in mapping.items():
            btn.setProperty("active", "true" if key == which else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)


class HomeView(QWidget):
    media_activated = pyqtSignal(str)
    filter_changed = pyqtSignal(str)
    search_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CenterStage")
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 12)
        root.setSpacing(14)

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName("SearchField")
        self.search.setPlaceholderText("Search your library…")
        self.search.textChanged.connect(self.search_changed.emit)
        top.addWidget(self.search, 1)
        root.addLayout(top)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        self._chip_buttons = {}
        for name in ("All", "Video", "Audio", "Recent"):
            btn = QPushButton(name)
            btn.setObjectName("Chip")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("active", "true" if name == "All" else "false")
            btn.clicked.connect(lambda _=False, n=name: self._select_chip(n))
            chips.addWidget(btn)
            self._chip_buttons[name] = btn
        chips.addStretch(1)
        root.addLayout(chips)

        header = QHBoxLayout()
        title = QLabel("Home")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.hint = QLabel("Open a file or folder to build your library")
        self.hint.setObjectName("SectionLink")
        header.addWidget(self.hint)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 8, 8)
        self.grid.setSpacing(14)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scroll.setWidget(self.grid_host)
        root.addWidget(self.scroll, 1)

        self._paths: List[str] = []

    def _select_chip(self, name: str) -> None:
        for key, btn in self._chip_buttons.items():
            btn.setProperty("active", "true" if key == name else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.filter_changed.emit(name.lower())

    def set_items(self, paths: List[str], thumbnails: Optional[dict] = None) -> None:
        self._paths = list(paths)
        thumbnails = thumbnails or {}
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        if not paths:
            empty = QLabel("No media yet — use + or Open Folder from the rail.")
            empty.setObjectName("MetaSecondary")
            empty.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 24px;")
            self.grid.addWidget(empty, 0, 0)
            return
        cols = 4
        for i, path in enumerate(paths):
            title = os.path.basename(path)
            if len(title) > 42:
                title = title[:39] + "…"
            sub = os.path.splitext(path)[1].upper().lstrip(".") or "MEDIA"
            card = MediaCard(title, sub, path, thumbnail_path=thumbnails.get(path))
            card.clicked.connect(self.media_activated.emit)
            self.grid.addWidget(card, i // cols, i % cols)


class NowPlayingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NowPlayingPanel")
        self.setFixedWidth(280)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        head = QLabel("Now playing")
        head.setObjectName("SectionLink")
        layout.addWidget(head)

        self.art = QLabel("VoxPlayer")
        self.art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art.setMinimumHeight(200)
        self.art.setStyleSheet(
            f"""
            QLabel {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {COLORS['bg_input']}, stop:1 {COLORS['bg_elevated']});
                border-radius: 12px;
                color: {COLORS['accent']};
                font-size: 22px;
                font-weight: 700;
            }}
            """
        )
        layout.addWidget(self.art)

        self.title = QLabel("Nothing playing")
        self.title.setObjectName("MetaPrimary")
        self.title.setWordWrap(True)
        layout.addWidget(self.title)

        self.subtitle = QLabel("Drop a file or pick from Home")
        self.subtitle.setObjectName("MetaSecondary")
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)

        self.engine_label = QLabel("Engine: —")
        self.engine_label.setObjectName("MetaMuted")
        layout.addWidget(self.engine_label)

        queue_label = QLabel("Up next")
        queue_label.setObjectName("SectionLink")
        layout.addWidget(queue_label)

        self.queue = QListWidget()
        self.queue.setObjectName("QueueList")
        layout.addWidget(self.queue, 1)

    def update_now_playing(
        self,
        path: Optional[str],
        engine: str = "",
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
    ) -> None:
        if not path:
            self.title.setText("Nothing playing")
            self.subtitle.setText("Drop a file or pick from Home")
            self.art.clear()
            self.art.setText("VoxPlayer")
            return
        name = title or os.path.basename(path)
        self.title.setText(name)
        self.subtitle.setText(subtitle or os.path.dirname(path))
        if thumbnail_path and os.path.isfile(thumbnail_path):
            self.set_art_pixmap(thumbnail_path)
        else:
            ext = os.path.splitext(path)[1].lower()
            self.art.clear()
            self.art.setText(
                "▶ VIDEO"
                if ext in {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}
                else "♪ AUDIO"
            )
        if engine:
            self.engine_label.setText(f"Engine: {engine}")

    def set_art_pixmap(self, image_path: str = "", pixmap: Optional[QPixmap] = None) -> None:
        pix = pixmap
        if pix is None and image_path and os.path.isfile(image_path):
            pix = QPixmap(image_path)
        if pix is None or pix.isNull():
            return
        self.art.setText("")
        target_w = max(200, self.art.width() or 248)
        target_h = max(160, self.art.minimumHeight())
        self.art.setPixmap(
            pix.scaled(
                target_w,
                target_h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def set_queue(self, paths: List[str], current: Optional[str] = None) -> None:
        self.queue.clear()
        for path in paths[:40]:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            if current and path == current:
                item.setText(f"▸ {os.path.basename(path)}")
            self.queue.addItem(item)


class TransportBar(QWidget):
    """Bottom persistent transport — API compatible with legacy PlayerControls callers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("TransportBar")
        self.setFixedHeight(76)
        self.setup_ui()

    def setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 8)
        root.setSpacing(12)

        # Left: track meta
        left = QHBoxLayout()
        left.setSpacing(10)
        self.track_art = QLabel("VX")
        self.track_art.setFixedSize(48, 48)
        self.track_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.track_art.setStyleSheet(
            f"background:{COLORS['bg_elevated']}; border-radius:6px; color:{COLORS['accent']}; font-weight:700;"
        )
        left.addWidget(self.track_art)
        meta = QVBoxLayout()
        meta.setSpacing(2)
        self.track_title = QLabel("VoxPlayer")
        self.track_title.setStyleSheet(f"color:{COLORS['text']}; font-weight:600; font-size:13px;")
        self.track_artist = QLabel("Ready")
        self.track_artist.setStyleSheet(f"color:{COLORS['text_muted']}; font-size:11px;")
        meta.addWidget(self.track_title)
        meta.addWidget(self.track_artist)
        left.addLayout(meta)
        root.addLayout(left, 2)

        # Center: transport
        center = QVBoxLayout()
        center.setSpacing(4)
        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        buttons.addStretch(1)
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setObjectName("TransportGhost")
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("TransportPrimary")
        self.btn_play.setFixedSize(36, 36)
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setObjectName("TransportGhost")
        self.btn_next = QPushButton("⏭")
        self.btn_next.setObjectName("TransportGhost")
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setObjectName("TransportGhost")
        for b in (self.btn_prev, self.btn_play, self.btn_stop, self.btn_next):
            buttons.addWidget(b)
        buttons.addStretch(1)
        center.addLayout(buttons)

        seek_row = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("timeLabel")
        self.time_label.setStyleSheet(
            f"color:{COLORS['text_muted']}; font-family:{COLORS.get('mono', 'monospace')}; font-size:11px; min-width:96px;"
        )
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        seek_row.addWidget(self.time_label)
        seek_row.addWidget(self.seek_slider, 1)
        center.addLayout(seek_row)
        root.addLayout(center, 4)

        # Right: volume + fullscreen affordance
        right = QHBoxLayout()
        right.setSpacing(6)
        right.addWidget(self.btn_mute)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 200)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(110)
        self.volume_label = QLabel("100%")
        self.volume_label.setObjectName("volumeLabel")
        self.volume_label.setStyleSheet(f"color:{COLORS['text_muted']}; font-size:11px; min-width:36px;")
        right.addWidget(self.volume_slider)
        right.addWidget(self.volume_label)
        root.addLayout(right, 2)

        self.seek_slider.setMouseTracking(True)
        self.seek_slider.enterEvent = self.on_seek_hover
        self.seek_slider.leaveEvent = self.on_seek_leave
        self.seek_slider.mouseMoveEvent = self.on_seek_mouse_move

        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_mute.clicked.connect(self.toggle_mute)
        self.btn_prev.clicked.connect(self.previous_media)
        self.btn_next.clicked.connect(self.next_media)
        self.seek_slider.valueChanged.connect(self.seek_changed)
        self.volume_slider.valueChanged.connect(self.volume_changed)

    def set_track_meta(self, title: str, subtitle: str = "") -> None:
        self.track_title.setText(title or "VoxPlayer")
        self.track_artist.setText(subtitle or "Ready")

    def set_track_art(self, image_path: str = "", pixmap: Optional[QPixmap] = None) -> None:
        pix = pixmap
        if pix is None and image_path and os.path.isfile(image_path):
            pix = QPixmap(image_path)
        if pix is None or pix.isNull():
            self.track_art.setText("VX")
            self.track_art.setPixmap(QPixmap())
            return
        self.track_art.setText("")
        self.track_art.setPixmap(
            pix.scaled(
                48,
                48,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def toggle_play(self):
        if hasattr(self.parent_window, "toggle_playback"):
            self.parent_window.toggle_playback()

    def stop(self):
        if hasattr(self.parent_window, "stop_playback"):
            self.parent_window.stop_playback()

    def toggle_mute(self):
        if hasattr(self.parent_window, "toggle_mute"):
            self.parent_window.toggle_mute()

    def previous_media(self):
        if hasattr(self.parent_window, "previous_media"):
            self.parent_window.previous_media()

    def next_media(self):
        if hasattr(self.parent_window, "next_media"):
            self.parent_window.next_media()

    def seek_changed(self, value):
        if hasattr(self.parent_window, "seek_to_position"):
            self.parent_window.seek_to_position(value / 1000.0)

    def volume_changed(self, value):
        if hasattr(self.parent_window, "set_volume"):
            self.parent_window.set_volume(value)
        self.volume_label.setText(f"{value}%")

    def on_seek_hover(self, event):
        if hasattr(self.parent_window, "show_timeline_preview"):
            self.parent_window.show_timeline_preview(True)

    def on_seek_leave(self, event):
        if hasattr(self.parent_window, "show_timeline_preview"):
            self.parent_window.show_timeline_preview(False)

    def on_seek_mouse_move(self, event):
        if hasattr(self.parent_window, "update_timeline_preview"):
            pos = event.position().x()
            width = self.seek_slider.width()
            if width > 0:
                self.parent_window.update_timeline_preview(pos / width)

    def update_time(self, current, total):
        def format_time(ms):
            seconds = max(0, int(ms // 1000))
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"

        self.time_label.setText(f"{format_time(current)} / {format_time(total)}")

    def update_seek_position(self, position):
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(int(position * 1000))
        self.seek_slider.blockSignals(False)
