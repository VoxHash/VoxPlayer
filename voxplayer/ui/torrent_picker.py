"""Tree picker for multi-file torrents (folder / season layout)."""

from __future__ import annotations

import os
from typing import List, Optional, Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..media.torrent_gate import MEDIA_EXTENSIONS, VIDEO_EXTENSIONS, AUDIO_EXTENSIONS
from ..theme import COLORS


def media_paths_only(paths: Sequence[str]) -> List[str]:
    out = []
    for p in paths:
        if os.path.splitext(p)[1].lower() in MEDIA_EXTENSIONS:
            out.append(p.replace("\\", "/"))
    return sorted(out)


class TorrentFilePickerDialog(QDialog):
    """Show torrent media files in a folder tree; user can check many files."""

    def __init__(self, paths: Sequence[str], parent=None, title: str = "Torrent contents"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(560, 460)
        self.setStyleSheet(
            f"QDialog {{ background: {COLORS['bg_app']}; color: {COLORS['text']}; }}"
            f"QTreeWidget {{ background: {COLORS['bg_panel']}; border: 1px solid {COLORS['border']};"
            f" border-radius: 8px; padding: 4px; }}"
            f"QLabel {{ color: {COLORS['text_muted']}; }}"
        )
        self._selected: List[str] = []
        media = media_paths_only(paths)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Check one or more audio/video files from any folder. "
                "Folders (e.g. seasons) can be expanded. "
                f"{len(media)} media file(s) found."
            )
        )
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type"])
        self.tree.setColumnWidth(0, 380)
        self.tree.setUniformRowHeights(True)
        layout.addWidget(self.tree, 1)

        root_nodes: dict = {}
        for path in media:
            parts = [p for p in path.split("/") if p]
            if not parts:
                continue
            parent_item = None
            trail = ""
            for i, part in enumerate(parts):
                trail = f"{trail}/{part}" if trail else part
                is_file = i == len(parts) - 1
                key = trail
                if key in root_nodes:
                    parent_item = root_nodes[key]
                    continue
                item = QTreeWidgetItem([part, ""])
                item.setFlags(
                    item.flags()
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsAutoTristate
                )
                item.setCheckState(0, Qt.CheckState.Unchecked)
                if is_file:
                    ext = os.path.splitext(part)[1].lower()
                    kind = (
                        "Video"
                        if ext in VIDEO_EXTENSIONS
                        else "Audio"
                        if ext in AUDIO_EXTENSIONS
                        else "Media"
                    )
                    item.setText(1, kind)
                    item.setData(0, Qt.ItemDataRole.UserRole, path)
                else:
                    item.setText(1, "Folder")
                if parent_item is None:
                    self.tree.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)
                root_nodes[key] = item
                parent_item = item

        self.tree.expandToDepth(0)
        self.tree.itemChanged.connect(self._on_item_changed)

        row = QHBoxLayout()
        btn_all = QPushButton("Select all media")
        btn_none = QPushButton("Clear selection")
        btn_all.clicked.connect(self._select_all_media)
        btn_none.clicked.connect(self._clear_selection)
        row.addWidget(btn_all)
        row.addWidget(btn_none)
        row.addStretch(1)
        layout.addLayout(row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_current)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 0:
            return
        # Propagate folder check state to media children.
        if item.data(0, Qt.ItemDataRole.UserRole):
            return
        state = item.checkState(0)
        if state == Qt.CheckState.PartiallyChecked:
            return
        self.tree.blockSignals(True)
        self._set_children_check(item, state)
        self.tree.blockSignals(False)

    def _set_children_check(self, item: QTreeWidgetItem, state: Qt.CheckState) -> None:
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self._set_children_check(child, state)

    def _iter_media_items(self, item: Optional[QTreeWidgetItem] = None):
        if item is None:
            for i in range(self.tree.topLevelItemCount()):
                yield from self._iter_media_items(self.tree.topLevelItem(i))
            return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            yield item
        for i in range(item.childCount()):
            yield from self._iter_media_items(item.child(i))

    def _select_all_media(self) -> None:
        self.tree.blockSignals(True)
        for item in self._iter_media_items():
            item.setCheckState(0, Qt.CheckState.Checked)
        self.tree.blockSignals(False)

    def _clear_selection(self) -> None:
        self.tree.blockSignals(True)
        for item in self._iter_media_items():
            item.setCheckState(0, Qt.CheckState.Unchecked)
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            top.setCheckState(0, Qt.CheckState.Unchecked)
            self._set_children_check(top, Qt.CheckState.Unchecked)
        self.tree.blockSignals(False)

    def _checked_paths(self) -> List[str]:
        paths: List[str] = []
        for item in self._iter_media_items():
            if item.checkState(0) == Qt.CheckState.Checked:
                path = item.data(0, Qt.ItemDataRole.UserRole)
                if path:
                    paths.append(str(path))
        return paths

    def _accept_current(self) -> None:
        paths = self._checked_paths()
        if not paths:
            # Fallback: current item if it is a media file
            item = self.tree.currentItem()
            if item is not None:
                path = item.data(0, Qt.ItemDataRole.UserRole)
                if path:
                    paths = [str(path)]
        if not paths:
            return
        self._selected = paths
        self.accept()

    def selected_path(self) -> Optional[str]:
        """First selected path (compat)."""
        return self._selected[0] if self._selected else None

    def selected_paths(self) -> List[str]:
        return list(self._selected)
