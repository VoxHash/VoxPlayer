"""MPRIS2 desktop media control (Linux) via QtDBus — no extra deps.

Exposes ``org.mpris.MediaPlayer2.voxplayer`` so GNOME/KDE media keys and
shell widgets can drive the native-engine player.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import QObject, pyqtClassInfo, pyqtSlot, pyqtProperty, pyqtSignal
from PyQt6.QtDBus import (
    QDBusConnection,
    QDBusAbstractAdaptor,
    QDBusMessage,
    QDBusVariant,
)

SERVICE = "org.mpris.MediaPlayer2.voxplayer"
OBJECT_PATH = "/org/mpris/MediaPlayer2"
IFACE_ROOT = "org.mpris.MediaPlayer2"
IFACE_PLAYER = "org.mpris.MediaPlayer2.Player"
IFACE_PROPS = "org.freedesktop.DBus.Properties"


def _available() -> bool:
    return sys.platform.startswith("linux")


@pyqtClassInfo("D-Bus Interface", IFACE_ROOT)
class _RootAdaptor(QDBusAbstractAdaptor):
    def __init__(self, parent: QObject, host: "MprisController"):
        super().__init__(parent)
        self._host = host
        self.setAutoRelaySignals(True)

    @pyqtProperty(bool)
    def CanQuit(self) -> bool:
        return True

    @pyqtProperty(bool)
    def CanRaise(self) -> bool:
        return True

    @pyqtProperty(bool)
    def HasTrackList(self) -> bool:
        return False

    @pyqtProperty(str)
    def Identity(self) -> str:
        return "VoxPlayer"

    @pyqtProperty(str)
    def DesktopEntry(self) -> str:
        return "voxplayer"

    @pyqtProperty("QStringList")
    def SupportedUriSchemes(self):
        return ["file", "http", "https"]

    @pyqtProperty("QStringList")
    def SupportedMimeTypes(self):
        return [
            "audio/mpeg",
            "audio/flac",
            "audio/ogg",
            "audio/mp4",
            "video/mp4",
            "video/x-matroska",
            "video/webm",
        ]

    @pyqtSlot()
    def Raise(self) -> None:
        self._host.invoke("raise_window")

    @pyqtSlot()
    def Quit(self) -> None:
        self._host.invoke("quit_app")


@pyqtClassInfo("D-Bus Interface", IFACE_PLAYER)
class _PlayerAdaptor(QDBusAbstractAdaptor):
    Seeked = pyqtSignal("qint64")

    def __init__(self, parent: QObject, host: "MprisController"):
        super().__init__(parent)
        self._host = host
        self.setAutoRelaySignals(True)

    @pyqtProperty(str)
    def PlaybackStatus(self) -> str:
        return self._host.playback_status()

    @pyqtProperty(str)
    def LoopStatus(self) -> str:
        return self._host.loop_status()

    @LoopStatus.setter
    def LoopStatus(self, value: str) -> None:
        self._host.set_loop_status(value)

    @pyqtProperty(float)
    def Rate(self) -> float:
        fn = self._host._callbacks.get("rate") if hasattr(self._host, "_callbacks") else None
        try:
            return float(fn()) if callable(fn) else 1.0
        except Exception:
            return 1.0

    @Rate.setter
    def Rate(self, value: float) -> None:
        fn = self._host._callbacks.get("set_rate") if hasattr(self._host, "_callbacks") else None
        if callable(fn):
            fn(float(value))

    @pyqtProperty(bool)
    def Shuffle(self) -> bool:
        return self._host.shuffle()

    @Shuffle.setter
    def Shuffle(self, value: bool) -> None:
        self._host.set_shuffle(bool(value))

    @pyqtProperty("QVariantMap")
    def Metadata(self):
        return self._host.metadata()

    @pyqtProperty(float)
    def Volume(self) -> float:
        return self._host.volume()

    @Volume.setter
    def Volume(self, value: float) -> None:
        self._host.set_volume(float(value))

    @pyqtProperty("qlonglong")
    def Position(self) -> int:
        return int(self._host.position_us())

    @pyqtProperty(float)
    def MinimumRate(self) -> float:
        return 0.25

    @pyqtProperty(float)
    def MaximumRate(self) -> float:
        return 3.0

    @pyqtProperty(bool)
    def CanGoNext(self) -> bool:
        return True

    @pyqtProperty(bool)
    def CanGoPrevious(self) -> bool:
        return True

    @pyqtProperty(bool)
    def CanPlay(self) -> bool:
        return True

    @pyqtProperty(bool)
    def CanPause(self) -> bool:
        return True

    @pyqtProperty(bool)
    def CanSeek(self) -> bool:
        return True

    @pyqtProperty(bool)
    def CanControl(self) -> bool:
        return True

    @pyqtSlot()
    def Next(self) -> None:
        self._host.invoke("next")

    @pyqtSlot()
    def Previous(self) -> None:
        self._host.invoke("previous")

    @pyqtSlot()
    def Pause(self) -> None:
        self._host.invoke("pause")

    @pyqtSlot()
    def PlayPause(self) -> None:
        self._host.invoke("play_pause")

    @pyqtSlot()
    def Stop(self) -> None:
        self._host.invoke("stop")

    @pyqtSlot()
    def Play(self) -> None:
        self._host.invoke("play")

    @pyqtSlot("qlonglong")
    def Seek(self, offset: int) -> None:
        self._host.seek_us(int(offset))

    @pyqtSlot(str, "qlonglong")
    def SetPosition(self, _track_id: str, position: int) -> None:
        self._host.set_position_us(int(position))

    @pyqtSlot(str)
    def OpenUri(self, uri: str) -> None:
        self._host.invoke("open_uri", uri)


class MprisController(QObject):
    """Owns the D-Bus service and relays commands to the main window callbacks."""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._callbacks: Dict[str, Callable[..., Any]] = {}
        self._enabled = False
        self._root = None
        self._player = None
        self._bus: Optional[QDBusConnection] = None

    def set_callbacks(self, **kwargs: Callable[..., Any]) -> None:
        self._callbacks.update(kwargs)

    def invoke(self, name: str, *args) -> None:
        fn = self._callbacks.get(name)
        if callable(fn):
            try:
                fn(*args) if args else fn()
            except Exception:
                pass

    def start(self) -> bool:
        if not _available():
            return False
        if os.environ.get("VOXPLAYER_DISABLE_MPRIS", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }:
            return False
        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            return False
        bus.registerService(SERVICE)
        holder = QObject(self)
        holder.setObjectName("mpris")
        self._root = _RootAdaptor(holder, self)
        self._player = _PlayerAdaptor(holder, self)
        if not bus.registerObject(
            OBJECT_PATH,
            holder,
            QDBusConnection.RegisterOption.ExportAdaptors,
        ):
            return False
        self._bus = bus
        self._enabled = True
        return True

    def stop(self) -> None:
        if self._bus is not None:
            try:
                self._bus.unregisterObject(OBJECT_PATH)
                self._bus.unregisterService(SERVICE)
            except Exception:
                pass
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def playback_status(self) -> str:
        fn = self._callbacks.get("playback_status")
        return str(fn()) if callable(fn) else "Stopped"

    def loop_status(self) -> str:
        fn = self._callbacks.get("loop_status")
        return str(fn()) if callable(fn) else "None"

    def set_loop_status(self, value: str) -> None:
        fn = self._callbacks.get("set_loop_status")
        if callable(fn):
            fn(value)

    def shuffle(self) -> bool:
        fn = self._callbacks.get("shuffle")
        return bool(fn()) if callable(fn) else False

    def set_shuffle(self, value: bool) -> None:
        fn = self._callbacks.get("set_shuffle")
        if callable(fn):
            fn(value)

    def metadata(self) -> Dict[str, Any]:
        fn = self._callbacks.get("metadata")
        data = fn() if callable(fn) else {}
        return data if isinstance(data, dict) else {}

    def volume(self) -> float:
        fn = self._callbacks.get("volume")
        try:
            return max(0.0, min(1.0, float(fn()) if callable(fn) else 1.0))
        except Exception:
            return 1.0

    def set_volume(self, value: float) -> None:
        fn = self._callbacks.get("set_volume")
        if callable(fn):
            fn(max(0.0, min(1.0, float(value))))

    def position_us(self) -> int:
        fn = self._callbacks.get("position_us")
        try:
            return int(fn()) if callable(fn) else 0
        except Exception:
            return 0

    def seek_us(self, offset: int) -> None:
        fn = self._callbacks.get("seek_us")
        if callable(fn):
            fn(int(offset))

    def set_position_us(self, position: int) -> None:
        fn = self._callbacks.get("set_position_us")
        if callable(fn):
            fn(int(position))

    def notify_properties(self, changed: Optional[Dict[str, Any]] = None) -> None:
        if not self._enabled or self._bus is None:
            return
        props = changed or {
            "PlaybackStatus": self.playback_status(),
            "Metadata": self.metadata(),
            "Volume": self.volume(),
            "Shuffle": self.shuffle(),
            "LoopStatus": self.loop_status(),
        }
        packed = {key: QDBusVariant(val) for key, val in props.items()}
        msg = QDBusMessage.createSignal(OBJECT_PATH, IFACE_PROPS, "PropertiesChanged")
        msg.setArguments([IFACE_PLAYER, packed, []])
        self._bus.send(msg)
