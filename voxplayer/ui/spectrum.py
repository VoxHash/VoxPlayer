"""Optional transport chrome: waveform strip + spectrum bars (real PCM via ffmpeg)."""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ..theme import COLORS


class WaveformStrip(QWidget):
    """Paint a mono amplitude envelope; optional playhead ratio 0..1."""

    seek_requested = pyqtSignal(float)  # 0..1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WaveformStrip")
        self.setFixedHeight(22)
        self._peaks: List[float] = []
        self._playhead = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Waveform (click to seek)")

    def set_peaks(self, peaks: List[float]) -> None:
        self._peaks = list(peaks or [])
        self.update()

    def set_playhead(self, ratio: float) -> None:
        self._playhead = max(0.0, min(1.0, float(ratio)))
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.width() > 0:
            self.seek_requested.emit(event.position().x() / self.width())
        super().mousePressEvent(event)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(COLORS.get("bg_input", "#0F141C")))
        if not self._peaks or w <= 0:
            p.end()
            return
        mid = h / 2.0
        accent = QColor(COLORS.get("accent", "#FF8A3D"))
        muted = QColor(COLORS.get("border", "#2A3548"))
        n = len(self._peaks)
        for x in range(w):
            idx = min(n - 1, int(x * n / w))
            amp = self._peaks[idx]
            half = max(1.0, amp * (h * 0.45))
            played = (x / w) <= self._playhead
            p.setPen(QPen(accent if played else muted, 1))
            p.drawLine(int(x), int(mid - half), int(x), int(mid + half))
        # playhead
        px = int(self._playhead * (w - 1))
        p.setPen(QPen(QColor(COLORS.get("text", "#F2F4F7")), 1))
        p.drawLine(px, 0, px, h)
        p.end()


class SpectrumMeter(QWidget):
    """Vertical bar spectrum meter for transport chrome."""

    def __init__(self, parent=None, bands: int = 32):
        super().__init__(parent)
        self.setObjectName("SpectrumMeter")
        self.setFixedHeight(28)
        self.setMinimumWidth(120)
        self._bands = bands
        self._levels: List[float] = [0.0] * bands
        self.setToolTip("Spectrum (from current track PCM)")

    def set_levels(self, levels: List[float]) -> None:
        if not levels:
            self._levels = [0.0] * self._bands
        else:
            # resample to fixed band count
            out: List[float] = []
            for i in range(self._bands):
                a = int(i * len(levels) / self._bands)
                b = int((i + 1) * len(levels) / self._bands)
                chunk = levels[a:max(a + 1, b)]
                out.append(max(0.0, min(1.0, max(chunk) if chunk else 0.0)))
            self._levels = out
        self.update()

    def clear(self) -> None:
        self._levels = [0.0] * self._bands
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(COLORS.get("bg_elevated", "#1A2330")))
        n = max(1, len(self._levels))
        gap = 1
        bar_w = max(2, (w - gap * (n + 1)) // n)
        accent = QColor(COLORS.get("accent", "#FF8A3D"))
        soft = QColor(COLORS.get("accent_hover", "#FFB070"))
        for i, level in enumerate(self._levels):
            bh = max(1, int(level * (h - 4)))
            x = gap + i * (bar_w + gap)
            y = h - 2 - bh
            color = soft if level > 0.75 else accent
            color.setAlpha(220)
            p.fillRect(x, y, bar_w, bh, color)
        p.end()
