"""
Modern VoxPlayer shell: left library rail, center home/stage, now-playing,
and bottom transport — layout patterns adapted for a unique Vox identity.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QObject
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
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
    QStackedWidget,
    QMenu,
    QDialog,
)

from ..theme import COLORS
from .marquee import MarqueeLabel


VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"}


class _MediaDropMixin:
    """Accept external file/folder URL drops; subclasses set drop_mode and files_dropped."""

    drop_mode = "play"  # "play" | "index"

    def _enable_drops(self) -> None:
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(local)
        if paths and hasattr(self, "files_dropped"):
            self.files_dropped.emit(paths, getattr(self, "drop_mode", "play"))
            event.acceptProposedAction()
            return
        event.ignore()


class MediaCard(QFrame):
    clicked = pyqtSignal(str)
    context_requested = pyqtSignal(str, object)  # path, global QPoint

    def __init__(
        self,
        title: str,
        subtitle: str,
        path: str,
        parent=None,
        thumbnail_path: Optional[str] = None,
        card_w: int = 160,
        card_h: int = 190,
    ):
        super().__init__(parent)
        self.path = path
        self.setObjectName("MediaCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(card_w, card_h)
        art_w = max(80, card_w - 20)
        art_h = max(70, card_h - 70)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.art = QLabel()
        self.art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art.setFixedSize(art_w, art_h)
        self.art.setStyleSheet(
            f"background: {COLORS['bg_input']}; border-radius: 8px; color: {COLORS['accent']}; font-size: 28px;"
        )
        ext = os.path.splitext(path)[1].lower()
        if thumbnail_path and os.path.isfile(thumbnail_path):
            self.set_thumbnail(thumbnail_path)
        else:
            self.art.setText("▶" if ext in VIDEO_EXT else "♪")
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
                self.art.width(),
                self.art.height(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.path)
        elif event.button() == Qt.MouseButton.RightButton:
            self.context_requested.emit(self.path, event.globalPosition().toPoint())
        super().mousePressEvent(event)


class LeftRail(QWidget):
    home_requested = pyqtSignal()
    library_requested = pyqtSignal()
    browse_requested = pyqtSignal()
    open_file_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()
    torrent_requested = pyqtSignal()
    favorites_requested = pyqtSignal()

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
        self.btn_browse = self._rail_btn("◎", "Browse by metadata")
        self.btn_favorites = self._rail_btn("★", "Favorites & playlists")
        self.btn_open = self._rail_btn("+", "Open file")
        self.btn_folder = self._rail_btn("📁", "Open folder")
        self.btn_torrent = self._rail_btn("↯", "Torrent")

        self.btn_home.clicked.connect(self.home_requested.emit)
        self.btn_library.clicked.connect(self.library_requested.emit)
        self.btn_browse.clicked.connect(self.browse_requested.emit)
        self.btn_favorites.clicked.connect(self.favorites_requested.emit)
        self.btn_open.clicked.connect(self.open_file_requested.emit)
        self.btn_folder.clicked.connect(self.open_folder_requested.emit)
        self.btn_torrent.clicked.connect(self.torrent_requested.emit)

        for b in (
            self.btn_home,
            self.btn_library,
            self.btn_browse,
            self.btn_favorites,
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
            "browse": self.btn_browse,
            "favorites": self.btn_favorites,
        }
        for key, btn in mapping.items():
            btn.setProperty("active", "true" if key == which else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)


class HomeView(_MediaDropMixin, QWidget):
    media_activated = pyqtSignal(str)
    filter_changed = pyqtSignal(str)
    search_changed = pyqtSignal(str)
    view_mode_changed = pyqtSignal(str)  # grid|list
    media_context = pyqtSignal(str, object)  # path, QPoint
    facet_selected = pyqtSignal(str, str)  # facet_key, bucket
    collection_selected = pyqtSignal(str)  # playlist name
    files_dropped = pyqtSignal(list, str)

    _PLAY_FACETS = ("recently", "never", "most_played")
    _AUDIO_FACETS = ("year", "genre", "artist", "album") + _PLAY_FACETS
    _VIDEO_FACETS = ("movies", "tv") + _PLAY_FACETS
    _ALL_FACETS = _PLAY_FACETS
    drop_mode = "index"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CenterStage")
        self._enable_drops()
        self._view_mode = "grid"
        self._paths: List[str] = []
        self._thumbnails: Dict[str, str] = {}
        self._card_w = 160
        self._card_h = 190
        self._browse_mode = False
        self._filter_name = "all"
        self._facets_enabled = True

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 12)
        root.setSpacing(14)

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName("SearchField")
        self.search.setPlaceholderText("Search your library…")
        self.search.textChanged.connect(self.search_changed.emit)
        top.addWidget(self.search, 1)

        self.btn_grid = QPushButton("▦")
        self.btn_grid.setObjectName("FilterIcon")
        self.btn_grid.setToolTip("Grid view")
        self.btn_grid.setFixedSize(36, 32)
        self.btn_grid.setProperty("active", "true")
        self.btn_grid.clicked.connect(lambda: self.set_view_mode("grid"))
        self.btn_list = QPushButton("☰")
        self.btn_list.setObjectName("FilterIcon")
        self.btn_list.setToolTip("List view")
        self.btn_list.setFixedSize(36, 32)
        self.btn_list.setProperty("active", "false")
        self.btn_list.clicked.connect(lambda: self.set_view_mode("list"))
        top.addWidget(self.btn_grid)
        top.addWidget(self.btn_list)
        root.addLayout(top)

        # Understated icon + label filter tabs (no heavy filled chips)
        chips = QHBoxLayout()
        chips.setSpacing(4)
        self._chip_buttons = {}
        filter_defs = (
            ("All", "▣", "All media"),
            ("Video", "▶", "Video only"),
            ("Audio", "♪", "Audio only"),
            ("Recent", "◷", "Recently added"),
        )
        for name, glyph, tip in filter_defs:
            btn = QPushButton(f"{glyph}  {name}")
            btn.setObjectName("FilterTab")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setProperty("active", "true" if name == "All" else "false")
            btn.clicked.connect(lambda _=False, n=name: self._select_chip(n))
            chips.addWidget(btn)
            self._chip_buttons[name] = btn
        chips.addStretch(1)
        root.addLayout(chips)

        # Facet browse row — Audio: Year/Genre/Artist · Video: Movies/TV Shows
        self.facet_row = QWidget()
        facet_layout = QHBoxLayout(self.facet_row)
        facet_layout.setContentsMargins(0, 0, 0, 0)
        facet_layout.setSpacing(8)
        self._facet_buttons = {}
        for key, label in (
            ("year", "Year"),
            ("genre", "Genre"),
            ("artist", "Artist"),
            ("album", "Album"),
            ("movies", "Movies"),
            ("tv", "TV Shows"),
            ("recently", "Recently"),
            ("never", "Never played"),
            ("most_played", "Most played"),
        ):
            btn = QPushButton(label)
            btn.setObjectName("Chip")
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda _=False, k=key: self._select_facet(k))
            facet_layout.addWidget(btn)
            self._facet_buttons[key] = btn
        facet_layout.addStretch(1)
        self.facet_row.hide()
        root.addWidget(self.facet_row)

        self.facet_buckets = QListWidget()
        self.facet_buckets.setObjectName("LibraryList")
        self.facet_buckets.setMaximumHeight(140)
        self.facet_buckets.hide()
        self.facet_buckets.itemClicked.connect(self._on_bucket_clicked)
        root.addWidget(self.facet_buckets)

        # Playlist / Favorites collection chips (Favorites page only)
        self.collection_row = QWidget()
        self._collection_layout = QHBoxLayout(self.collection_row)
        self._collection_layout.setContentsMargins(0, 0, 0, 0)
        self._collection_layout.setSpacing(8)
        self._collection_buttons: Dict[str, QPushButton] = {}
        self.collection_row.hide()
        root.addWidget(self.collection_row)

        header = QHBoxLayout()
        self.title_label = QLabel("Home")
        self.title_label.setObjectName("SectionTitle")
        header.addWidget(self.title_label)
        header.addStretch(1)
        self.hint = QLabel("Open a file or folder to build your library")
        self.hint.setObjectName("SectionLink")
        header.addWidget(self.hint)
        root.addLayout(header)

        self.content_stack = QStackedWidget()
        self.scroll = QScrollArea()
        self.scroll.setObjectName("LibraryScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setAcceptDrops(True)
        self.grid_host = QWidget()
        self.grid_host.setAcceptDrops(True)
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 12, 8)
        self.grid.setSpacing(14)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scroll.setWidget(self.grid_host)
        self.content_stack.addWidget(self.scroll)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("LibraryList")
        self.list_widget.setAcceptDrops(True)
        self.list_widget.itemActivated.connect(self._on_list_activated)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_list_context)
        self.content_stack.addWidget(self.list_widget)
        root.addWidget(self.content_stack, 1)

        self._active_facet = "year"
        self._facet_data: Dict[str, Dict[str, List[str]]] = {}

    def set_browse_mode(self, enabled: bool) -> None:
        self._browse_mode = bool(enabled)
        if self._browse_mode:
            self.title_label.setText("Browse")
        self._facets_enabled = True
        self._apply_facet_visibility()

    def set_facets_enabled(self, enabled: bool) -> None:
        """Hide facet UI on Favorites / non-library pages."""
        self._facets_enabled = bool(enabled)
        if not enabled:
            self.clear_collections()
        self._apply_facet_visibility()

    def set_facets(self, facets: Dict[str, Dict[str, List[str]]]) -> None:
        self._facet_data = facets or {}
        self._apply_facet_visibility()

    def _apply_facet_visibility(self) -> None:
        filt = (self._filter_name or "all").lower()
        if filt == "audio":
            allowed = self._AUDIO_FACETS
        elif filt == "video":
            allowed = self._VIDEO_FACETS
        elif filt in ("all", "recent"):
            allowed = self._ALL_FACETS
        else:
            allowed = ()
        show = self._facets_enabled and bool(allowed)
        for key, btn in self._facet_buttons.items():
            btn.setVisible(key in allowed)
        self.facet_row.setVisible(show)
        if not show:
            self.facet_buckets.hide()
            return
        if self._active_facet not in allowed:
            self._active_facet = allowed[0] if allowed else "year"
        self._select_facet(self._active_facet)
        self.facet_buckets.setVisible(True)

    def _select_facet(self, key: str) -> None:
        self._active_facet = key
        for k, btn in self._facet_buttons.items():
            btn.setProperty("active", "true" if k == key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.facet_buckets.clear()
        buckets = self._facet_data.get(key, {})
        for label, paths in buckets.items():
            item = QListWidgetItem(f"{label}  ({len(paths)})")
            item.setData(Qt.ItemDataRole.UserRole, label)
            self.facet_buckets.addItem(item)

    def _on_bucket_clicked(self, item: QListWidgetItem) -> None:
        label = item.data(Qt.ItemDataRole.UserRole)
        if label:
            self.facet_selected.emit(self._active_facet, label)

    def set_collections(self, names: List[str], active: str) -> None:
        """Show Favorites / playlist chips so named playlists are visible and selectable."""
        while self._collection_layout.count():
            item = self._collection_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._collection_buttons = {}
        if not names:
            self.collection_row.hide()
            return
        for name in names:
            btn = QPushButton(name)
            btn.setObjectName("Chip")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("active", "true" if name == active else "false")
            btn.clicked.connect(lambda _=False, n=name: self.collection_selected.emit(n))
            self._collection_layout.addWidget(btn)
            self._collection_buttons[name] = btn
        self._collection_layout.addStretch(1)
        self.collection_row.show()

    def clear_collections(self) -> None:
        while self._collection_layout.count():
            item = self._collection_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._collection_buttons = {}
        self.collection_row.hide()

    def set_view_mode(self, mode: str) -> None:
        mode = "list" if mode == "list" else "grid"
        self._view_mode = mode
        self.btn_grid.setProperty("active", "true" if mode == "grid" else "false")
        self.btn_list.setProperty("active", "true" if mode == "list" else "false")
        for b in (self.btn_grid, self.btn_list):
            b.style().unpolish(b)
            b.style().polish(b)
        self.content_stack.setCurrentWidget(self.list_widget if mode == "list" else self.scroll)
        self._render_items()
        self.view_mode_changed.emit(mode)

    def _select_chip(self, name: str) -> None:
        for key, btn in self._chip_buttons.items():
            btn.setProperty("active", "true" if key == name else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._filter_name = name.lower()
        self._apply_facet_visibility()
        self.filter_changed.emit(self._filter_name)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._view_mode == "grid" and self._paths:
            new_cols = self._columns_for_width()
            if getattr(self, "_last_cols", None) != new_cols:
                self._last_cols = new_cols
                self._render_items()

    def _columns_for_width(self) -> int:
        avail = max(200, self.scroll.viewport().width() - 16)
        gap = 14
        cols = max(1, (avail + gap) // (self._card_w + gap))
        return int(cols)

    def set_items(self, paths: List[str], thumbnails: Optional[dict] = None) -> None:
        self._paths = list(paths)
        self._thumbnails = thumbnails or {}
        self._render_items()

    def update_thumbnail(self, path: str, thumbnail_path: str) -> None:
        """Patch one card's art without rebuilding the whole grid."""
        if not path or not thumbnail_path or not os.path.isfile(thumbnail_path):
            return
        self._thumbnails[path] = thumbnail_path
        if self._view_mode == "list":
            return
        for i in range(self.grid.count()):
            item = self.grid.itemAt(i)
            w = item.widget() if item else None
            if w is not None and getattr(w, "path", None) == path:
                w.set_thumbnail(thumbnail_path)
                break

    def _clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _make_empty_state(self) -> QWidget:
        """Stronger empty library panel with clear next actions."""
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(32, 48, 32, 48)
        lay.setSpacing(10)
        title = QLabel("Your library is empty")
        title.setObjectName("SectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 20px; font-weight: 700;"
        )
        body = QLabel(
            "Add media to get started:\n"
            "• Open Folder from the left rail (roots are remembered next launch)\n"
            "• Drop files onto Home to index, or onto Now Playing / transport to play\n"
            "• Media → Open Files for a one-shot picker"
        )
        body.setObjectName("MetaSecondary")
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setWordWrap(True)
        body.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px; line-height: 1.4;"
        )
        formats = QLabel(
            "Supported formats include MP4, MKV, WebM, AVI, MP3, FLAC, M4A, Opus, OGG, WAV."
        )
        formats.setObjectName("MetaMuted")
        formats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formats.setWordWrap(True)
        formats.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        lay.addWidget(title)
        lay.addWidget(body)
        lay.addWidget(formats)
        return box

    def _render_items(self) -> None:
        paths = self._paths
        thumbs = self._thumbnails
        if self._view_mode == "list":
            self.list_widget.clear()
            if not paths:
                empty = QListWidgetItem(
                    "Library is empty\n"
                    "Open Folder from the rail, drop files here to index, "
                    "or use Media → Open Files.\n"
                    "Supported: MP4, MKV, WebM, MP3, FLAC, M4A, Opus, and more."
                )
                empty.setFlags(Qt.ItemFlag.NoItemFlags)
                self.list_widget.addItem(empty)
                return
            for path in paths:
                title = os.path.basename(path)
                sub = os.path.splitext(path)[1].upper().lstrip(".") or "MEDIA"
                item = QListWidgetItem(f"{title}    ·    {sub}")
                item.setData(Qt.ItemDataRole.UserRole, path)
                item.setToolTip(path)
                self.list_widget.addItem(item)
            return

        self._clear_grid()
        if not paths:
            self.grid.addWidget(self._make_empty_state(), 0, 0, 1, max(1, self._columns_for_width()))
            return
        cols = self._columns_for_width()
        self._last_cols = cols
        for i, path in enumerate(paths):
            title = os.path.basename(path)
            if len(title) > 42:
                title = title[:39] + "…"
            sub = os.path.splitext(path)[1].upper().lstrip(".") or "MEDIA"
            card = MediaCard(
                title,
                sub,
                path,
                thumbnail_path=thumbs.get(path),
                card_w=self._card_w,
                card_h=self._card_h,
            )
            card.clicked.connect(self.media_activated.emit)
            card.context_requested.connect(self.media_context.emit)
            self.grid.addWidget(card, i // cols, i % cols)

    def _on_list_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.media_activated.emit(path)

    def _on_list_context(self, pos) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.media_context.emit(path, self.list_widget.mapToGlobal(pos))


class ClickableArt(QLabel):
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class NowPlayingPanel(_MediaDropMixin, QWidget):
    art_clicked = pyqtSignal()
    expand_requested = pyqtSignal()
    minimize_requested = pyqtSignal()
    more_requested = pyqtSignal(object)  # QPoint
    queue_play_requested = pyqtSignal(str)
    queue_remove_requested = pyqtSignal(str)
    queue_clear_requested = pyqtSignal()
    add_to_playlist_requested = pyqtSignal(str, str)  # path, playlist_name
    files_dropped = pyqtSignal(list, str)

    drop_mode = "play"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NowPlayingPanel")
        self.setFixedWidth(300)
        self._enable_drops()
        self._current_path: Optional[str] = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header: title + more (Expand / Minimize live in the ⋯ menu only)
        header = QHBoxLayout()
        header.setSpacing(4)
        icon = QLabel("◉")
        icon.setStyleSheet(f"color: {COLORS['accent']}; font-size: 14px;")
        header.addWidget(icon)
        head = QLabel("Now playing")
        head.setObjectName("SectionLink")
        header.addWidget(head, 1)

        self.btn_more = QPushButton("⋯")
        self.btn_more.setObjectName("NpIconBtn")
        self.btn_more.setToolTip("More options")
        self.btn_more.setFixedSize(28, 28)
        self.btn_more.clicked.connect(
            lambda: self.more_requested.emit(self.btn_more.mapToGlobal(self.btn_more.rect().bottomLeft()))
        )
        header.addWidget(self.btn_more)
        layout.addLayout(header)

        self.art = ClickableArt("VoxPlayer")
        self.art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art.setMinimumHeight(220)
        self.art.setStyleSheet(
            f"""
            QLabel {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {COLORS['bg_input']}, stop:1 {COLORS['bg_elevated']});
                border-radius: 16px;
                color: {COLORS['accent']};
                font-size: 22px;
                font-weight: 700;
            }}
            """
        )
        self.art.clicked.connect(self.art_clicked.emit)
        layout.addWidget(self.art)

        self.title = MarqueeLabel("Nothing playing")
        self.title.setObjectName("MetaPrimary")
        self.title.setFixedHeight(22)
        layout.addWidget(self.title)

        self.subtitle = MarqueeLabel("Drop a file or pick from Home")
        self.subtitle.setObjectName("MetaSecondary")
        self.subtitle.setFixedHeight(18)
        layout.addWidget(self.subtitle)

        self.engine_label = QLabel("Engine: —")
        self.engine_label.setObjectName("MetaMuted")
        layout.addWidget(self.engine_label)

        queue_head = QHBoxLayout()
        queue_label = QLabel("Up next")
        queue_label.setObjectName("SectionLink")
        queue_head.addWidget(queue_label, 1)
        self.btn_clear_queue = QPushButton("⌫")
        self.btn_clear_queue.setObjectName("NpIconBtn")
        self.btn_clear_queue.setToolTip("Clear Up next and stop")
        self.btn_clear_queue.setFixedSize(28, 28)
        self.btn_clear_queue.clicked.connect(self.queue_clear_requested.emit)
        queue_head.addWidget(self.btn_clear_queue)
        layout.addLayout(queue_head)

        self.queue = QListWidget()
        self.queue.setObjectName("QueueList")
        self.queue.setAcceptDrops(True)
        self.queue.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue.itemClicked.connect(self._on_queue_click)
        self.queue.customContextMenuRequested.connect(self._on_queue_context)
        self.favorite_check = None  # optional callable(path) -> bool
        layout.addWidget(self.queue, 1)

    def _on_queue_click(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.queue_play_requested.emit(path)

    def _on_queue_context(self, pos) -> None:
        item = self.queue.itemAt(pos)
        menu = QMenu(self)
        if item:
            path = item.data(Qt.ItemDataRole.UserRole)
            remove = menu.addAction("Remove from Up next")
            in_fav = bool(self.favorite_check and path and self.favorite_check(path))
            fav = menu.addAction("Remove from Favorites" if in_fav else "Add to Favorites")
            chosen = menu.exec(self.queue.mapToGlobal(pos))
            if chosen == remove and path:
                self.queue_remove_requested.emit(path)
            elif chosen == fav and path:
                self.add_to_playlist_requested.emit(path, "Favorites")
        else:
            clear = menu.addAction("Clear Up next and stop")
            chosen = menu.exec(self.queue.mapToGlobal(pos))
            if chosen == clear:
                self.queue_clear_requested.emit()

    def update_now_playing(
        self,
        path: Optional[str],
        engine: str = "",
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
    ) -> None:
        self._current_path = path
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
            self.art.setText("▶ VIDEO" if ext in VIDEO_EXT else "♪ AUDIO")
        if engine:
            self.engine_label.setText(f"Engine: {engine}")

    def set_art_pixmap(self, image_path: str = "", pixmap: Optional[QPixmap] = None) -> None:
        pix = pixmap
        if pix is None and image_path and os.path.isfile(image_path):
            pix = QPixmap(image_path)
        if pix is None or pix.isNull():
            return
        # Reject near-black poster frames (common failed video grabs)
        if self._is_mostly_black(pix):
            return
        self.art.setText("")
        target_w = max(200, self.art.width() or 268)
        target_h = max(180, self.art.minimumHeight())
        rounded = pix.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.art.setPixmap(rounded)

    @staticmethod
    def _is_mostly_black(pix: QPixmap, sample: int = 24, threshold: int = 18) -> bool:
        img = pix.toImage()
        if img.isNull():
            return True
        w, h = img.width(), img.height()
        if w < 2 or h < 2:
            return True
        total = 0
        count = 0
        step_x = max(1, w // sample)
        step_y = max(1, h // sample)
        for y in range(0, h, step_y):
            for x in range(0, w, step_x):
                c = img.pixelColor(x, y)
                total += (c.red() + c.green() + c.blue()) // 3
                count += 1
        if count == 0:
            return True
        return (total / count) < threshold

    def set_queue(self, paths: List[str], current: Optional[str] = None) -> None:
        self.queue.clear()
        for path in paths[:80]:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            if current and path == current:
                item.setText(f"▸ {os.path.basename(path)}")
            self.queue.addItem(item)


class AboutDialog(QDialog):
    """Modern dimmed About modal — VoxPlayer branding only."""

    def __init__(self, version: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About VoxPlayer")
        self.setModal(True)
        self.setObjectName("AboutDialog")
        self.setFixedSize(420, 360)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("AboutCard")
        card.setStyleSheet(
            f"""
            QFrame#AboutCard {{
                background: {COLORS['bg_elevated']};
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(12)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("NpIconBtn")
        close_btn.setFixedSize(28, 28)
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

        mark = QLabel("VX")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 36px; font-weight: 800; letter-spacing: 2px;"
        )
        layout.addWidget(mark)

        name = QLabel("VoxPlayer")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 22px; font-weight: 700;"
        )
        layout.addWidget(name)

        ver = QLabel(f"Version {version}")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        layout.addWidget(ver)

        layout.addSpacing(8)
        blurb = QLabel("A modern desktop media player for your local library.")
        blurb.setWordWrap(True)
        blurb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        blurb.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(blurb)

        layout.addStretch(1)
        copy = QLabel("© VoxHash Technologies")
        copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copy.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(copy)

        root.addWidget(card)


class TransportBar(_MediaDropMixin, QWidget):
    """Bottom persistent transport — API compatible with legacy PlayerControls callers."""

    files_dropped = pyqtSignal(list, str)
    drop_mode = "play"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("TransportBar")
        self.setFixedHeight(76)
        self._enable_drops()
        self.setup_ui()

    def setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 8)
        root.setSpacing(12)

        left = QHBoxLayout()
        left.setSpacing(10)
        self.track_art = QLabel("VX")
        self.track_art.setFixedSize(48, 48)
        self.track_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.track_art.setStyleSheet(
            f"background:{COLORS['bg_elevated']}; border-radius:8px; color:{COLORS['accent']}; font-weight:700;"
        )
        left.addWidget(self.track_art)
        meta = QVBoxLayout()
        meta.setSpacing(2)
        self.track_title = MarqueeLabel("VoxPlayer")
        self.track_title.setStyleSheet(f"color:{COLORS['text']}; font-weight:600; font-size:13px;")
        self.track_title.setFixedHeight(18)
        self.track_artist = MarqueeLabel("Ready")
        self.track_artist.setStyleSheet(f"color:{COLORS['text_muted']}; font-size:11px;")
        self.track_artist.setFixedHeight(16)
        meta.addWidget(self.track_title)
        meta.addWidget(self.track_artist)
        left.addLayout(meta, 1)
        left_wrap = QWidget()
        left_wrap.setLayout(left)
        left_wrap.setMaximumWidth(280)
        root.addWidget(left_wrap, 2)

        center = QVBoxLayout()
        center.setSpacing(4)
        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        buttons.addStretch(1)
        self.btn_shuffle = QPushButton("⇄")
        self.btn_shuffle.setObjectName("TransportGhost")
        self.btn_shuffle.setToolTip("Shuffle")
        self.btn_shuffle.setCheckable(True)
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setObjectName("TransportGhost")
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("TransportPrimary")
        self.btn_play.setFixedSize(36, 36)
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setObjectName("TransportGhost")
        self.btn_next = QPushButton("⏭")
        self.btn_next.setObjectName("TransportGhost")
        self.btn_repeat = QPushButton("⟳")
        self.btn_repeat.setObjectName("TransportGhost")
        self.btn_repeat.setToolTip("Repeat: off")
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setObjectName("TransportGhost")
        for b in (
            self.btn_shuffle,
            self.btn_prev,
            self.btn_play,
            self.btn_stop,
            self.btn_next,
            self.btn_repeat,
        ):
            buttons.addWidget(b)
        buttons.addStretch(1)
        center.addLayout(buttons)

        seek_row = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("timeLabel")
        self.time_label.setStyleSheet(
            f"color:{COLORS['text_muted']}; font-family:monospace; font-size:11px; min-width:96px;"
        )
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        seek_row.addWidget(self.time_label)
        seek_row.addWidget(self.seek_slider, 1)
        center.addLayout(seek_row)
        root.addLayout(center, 4)

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
        self._seek_user_active = False
        self.seek_slider.installEventFilter(self)

        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_mute.clicked.connect(self.toggle_mute)
        self.btn_prev.clicked.connect(self.previous_media)
        self.btn_next.clicked.connect(self.next_media)
        self.btn_shuffle.clicked.connect(self.toggle_shuffle)
        self.btn_repeat.clicked.connect(self.cycle_repeat)
        # Do not seek on every valueChanged (playback poll updates the slider).
        self.seek_slider.sliderPressed.connect(self._seek_pressed)
        self.seek_slider.sliderMoved.connect(self._seek_moved)
        self.seek_slider.sliderReleased.connect(self._seek_released)
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
        if NowPlayingPanel._is_mostly_black(pix):
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

    def toggle_shuffle(self):
        if hasattr(self.parent_window, "toggle_shuffle"):
            self.parent_window.toggle_shuffle()

    def cycle_repeat(self):
        if hasattr(self.parent_window, "cycle_repeat_mode"):
            self.parent_window.cycle_repeat_mode()

    def sync_playback_modes(self, shuffle: bool, repeat_mode: str) -> None:
        """Reflect persisted shuffle / repeat on the transport chrome."""
        self.btn_shuffle.setChecked(bool(shuffle))
        self.btn_shuffle.setToolTip("Shuffle on" if shuffle else "Shuffle off")
        mode = repeat_mode if repeat_mode in ("off", "one", "all") else "off"
        labels = {
            "off": ("⟳", "Repeat off"),
            "all": ("⟳*", "Repeat all"),
            "one": ("⟳1", "Repeat one"),
        }
        text, tip = labels[mode]
        self.btn_repeat.setText(text)
        self.btn_repeat.setToolTip(tip)
        self.btn_repeat.setProperty("active", "true" if mode != "off" else "false")
        self.btn_repeat.style().unpolish(self.btn_repeat)
        self.btn_repeat.style().polish(self.btn_repeat)

    def _seek_pressed(self):
        self._seek_user_active = True

    def _seek_moved(self, value):
        if hasattr(self.parent_window, "seek_to_position"):
            self.parent_window.seek_to_position(value / 1000.0, exact=False)

    def _seek_released(self):
        self._seek_user_active = False
        if hasattr(self.parent_window, "seek_to_position"):
            self.parent_window.seek_to_position(self.seek_slider.value() / 1000.0, exact=True)

    def volume_changed(self, value):
        if hasattr(self.parent_window, "set_volume"):
            self.parent_window.set_volume(value)
        self.volume_label.setText(f"{value}%")

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self.seek_slider:
            et = event.type()
            if et == QEvent.Type.Enter:
                if hasattr(self.parent_window, "show_timeline_preview"):
                    self.parent_window.show_timeline_preview(True)
            elif et == QEvent.Type.Leave:
                if hasattr(self.parent_window, "show_timeline_preview"):
                    self.parent_window.show_timeline_preview(False)
            elif et == QEvent.Type.MouseMove:
                if hasattr(self.parent_window, "update_timeline_preview"):
                    width = self.seek_slider.width()
                    if width > 0:
                        pos = event.position().x()
                        self.parent_window.update_timeline_preview(pos / width)
        return super().eventFilter(obj, event)

    def update_time(self, current, total):
        def format_time(ms):
            seconds = max(0, int(ms // 1000))
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"

        self.time_label.setText(f"{format_time(current)} / {format_time(total)}")

    def update_seek_position(self, position):
        if self._seek_user_active:
            return
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(int(position * 1000))
        self.seek_slider.blockSignals(False)
