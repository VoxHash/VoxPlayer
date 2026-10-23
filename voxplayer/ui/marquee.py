"""Scrolling / elided labels so long titles do not push transport controls."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QFontMetrics
from PyQt6.QtWidgets import QWidget, QSizePolicy


class MarqueeLabel(QWidget):
    """Show partial text; slowly scroll when the string does not fit."""

    def __init__(self, text: str = "", parent=None, scroll_ms: int = 40):
        super().__init__(parent)
        self._full = text or ""
        self._offset = 0
        self._pause = 0
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(80)
        self.setFixedHeight(18)
        self._timer = QTimer(self)
        self._timer.setInterval(scroll_ms)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def setText(self, text: str) -> None:
        self._full = text or ""
        self._offset = 0
        self._pause = 25
        self.update()

    def text(self) -> str:
        return self._full

    def _overflow(self) -> int:
        fm = QFontMetrics(self.font())
        return max(0, fm.horizontalAdvance(self._full) - self.width() + 8)

    def _tick(self) -> None:
        overflow = self._overflow()
        if overflow <= 0:
            if self._offset:
                self._offset = 0
                self.update()
            return
        if self._pause > 0:
            self._pause -= 1
            return
        self._offset += 1
        if self._offset > overflow + 40:
            self._offset = 0
            self._pause = 35
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        fm = QFontMetrics(self.font())
        y = (self.height() + fm.ascent() - fm.descent()) // 2
        overflow = self._overflow()
        if overflow <= 0:
            painter.drawText(0, y, self._full)
            return
        painter.setClipRect(QRect(0, 0, self.width(), self.height()))
        painter.drawText(-self._offset, y, self._full)

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        return fm.size(0, self._full or " ")
