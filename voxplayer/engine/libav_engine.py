"""
FOSS libav decode backend (PyAV → system/bundled FFmpeg libraries).

Feature-flag: ``VOXPLAYER_DECODE=libav`` (aliases: ffmpeg, foss, av).
Default remains libvlc via ``PlaybackEngine``.

Parity goals vs native core:
  • play / pause / stop / seek / position / duration
  • volume 0–200% + mute (PCM gain)
  • video embed by painting RGB frames onto the Qt surface (no libvlc WID)

Audio out uses Qt ``QAudioSink`` (output device only — demux/decode stay in libav).
Requires optional dependency: ``pip install \"voxplayer[libav]\"`` (PyAV).
"""

from __future__ import annotations

import array
import os
import sys
import threading
import time
from typing import List, Optional, Tuple

from PyQt6.QtCore import QEvent, QIODevice, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QWidget

from .playback import (
    BackendKind,
    NativeEngineError,
    configure_embed_surface,
    embed_platform_hint,
    embed_status_message,
)


def libav_available() -> Tuple[bool, str]:
    try:
        import av  # noqa: F401

        return True, f"PyAV {getattr(__import__('av'), '__version__', '?')}"
    except Exception as exc:
        return False, str(exc)


def libav_install_hint() -> str:
    return "\n".join(
        [
            "VOXPLAYER_DECODE=libav requires the FOSS PyAV binding to FFmpeg libraries.",
            "  .venv/bin/pip install \"voxplayer[libav]\"",
            "  # or: .venv/bin/pip install av",
            "System FFmpeg shared libraries must be present (Arch: pacman -S ffmpeg).",
            "Default decode remains libvlc (unset VOXPLAYER_DECODE or set libvlc).",
        ]
    )


class _PcmQueueDevice(QIODevice):
    """Thread-safe PCM byte queue consumed by QAudioSink."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._closed = False

    def append(self, data: bytes) -> None:
        if not data or self._closed:
            return
        with self._lock:
            self._buf.extend(data)
            # Bound memory (~2s of stereo s16 @ 48k)
            max_bytes = 48000 * 2 * 2 * 2
            if len(self._buf) > max_bytes:
                overflow = len(self._buf) - max_bytes
                del self._buf[:overflow]

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()

    def bytesAvailable(self) -> int:  # noqa: N802
        with self._lock:
            return len(self._buf) + super().bytesAvailable()

    def readData(self, maxlen: int) -> bytes:  # noqa: N802
        with self._lock:
            if not self._buf:
                return b""
            n = min(maxlen, len(self._buf))
            chunk = bytes(self._buf[:n])
            del self._buf[:n]
            return chunk

    def writeData(self, data: bytes) -> int:  # noqa: N802
        return 0

    def close_queue(self) -> None:
        self._closed = True
        self.clear()


class LibavPlaybackEngine(QObject):
    """PlaybackEngine-compatible API backed by PyAV (libavcodec/libavformat)."""

    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    state_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    backend_ready = pyqtSignal(str)
    embed_changed = pyqtSignal(bool)

    def __init__(self, video_widget: QWidget, parent=None):
        super().__init__(parent)
        ok, detail = libav_available()
        if not ok:
            raise NativeEngineError(libav_install_hint() + f"\n\nImport error: {detail}")

        self.video_widget = video_widget
        self.backend = BackendKind.LIBAV
        self.media_player = None
        self.audio_output = None

        self._source_path = ""
        self._duration_ms = 0
        self._position_ms = 0
        self._volume_pct = 100
        self._muted = False
        self._last_state = "stopped"
        self._video_bound = False
        self._embed_hint = "libav-rgb"
        self._frame_image: Optional[QImage] = None
        self._next_path = ""

        self._lock = threading.Lock()
        self._worker: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._pause_flag = threading.Event()
        self._pause_flag.set()  # start paused until play()
        self._seek_ms: Optional[int] = None
        self._load_token = 0

        self._pcm = _PcmQueueDevice(self)
        self._pcm.open(QIODevice.OpenModeFlag.ReadOnly)
        self._sink = None
        self._sample_rate = 48000
        self._channels = 2
        self._playback_rate = 1.0

        configure_embed_surface(video_widget)
        if video_widget is not None:
            video_widget.installEventFilter(self)

        self._poll = QTimer(self)
        self._poll.setInterval(100)
        self._poll.timeout.connect(self._tick)
        self._poll.start()

        self._init_audio_sink()
        self.backend_ready.emit("libav")
        self.embed_changed.emit(True)
        self._video_bound = True

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self.video_widget and event.type() == QEvent.Type.Paint:
            if self._frame_image is not None and not self._frame_image.isNull():
                painter = QPainter(self.video_widget)
                painter.fillRect(self.video_widget.rect(), Qt.GlobalColor.black)
                img = self._frame_image.scaled(
                    self.video_widget.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = (self.video_widget.width() - img.width()) // 2
                y = (self.video_widget.height() - img.height()) // 2
                painter.drawImage(x, y, img)
                painter.end()
                return True
        return False

    def _init_audio_sink(self) -> None:
        from PyQt6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

        fmt = QAudioFormat()
        fmt.setSampleRate(self._sample_rate)
        fmt.setChannelCount(self._channels)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        device = QMediaDevices.defaultAudioOutput()
        if not device.isFormatSupported(fmt):
            fmt = device.preferredFormat()
            self._sample_rate = fmt.sampleRate() or 48000
            self._channels = fmt.channelCount() or 2
        self._sink = QAudioSink(device, fmt, self)
        self._sink.setBufferSize(self._sample_rate * self._channels * 2 // 2)
        self._sink.start(self._pcm)

    # --- API parity ---

    @property
    def backend_name(self) -> str:
        return self.backend.value

    @property
    def has_embedded_video(self) -> bool:
        return bool(self._video_bound and self._looks_like_video(self._source_path))

    @property
    def embed_limited(self) -> bool:
        return False

    @property
    def embed_platform(self) -> str:
        return self._embed_hint

    def refresh_embed_hint(self) -> str:
        self._embed_hint = "libav-rgb"
        return self._embed_hint

    def list_audio_output_devices(self) -> List[Tuple[str, str]]:
        try:
            from PyQt6.QtMultimedia import QMediaDevices

            out = []
            for d in QMediaDevices.audioOutputs():
                out.append((d.id().data().decode("utf-8", "replace"), d.description()))
            return out
        except Exception:
            return []

    def set_audio_output_device(self, device_id: Optional[str]) -> bool:
        # Recreate sink on default for now; device switch best-effort
        try:
            self._init_audio_sink()
            return True
        except Exception:
            return False

    def current_audio_output_device(self) -> str:
        return "default"

    def set_source(self, file_path: str) -> None:
        self._begin_load(file_path, start_paused=True)

    def play(self) -> None:
        self._pause_flag.clear()
        if self._worker is None or not self._worker.is_alive():
            if self._source_path:
                self._begin_load(self._source_path, start_paused=False)
                return
        self._set_state("playing")

    def pause(self) -> None:
        self._pause_flag.set()
        self._set_state("paused")

    def stop(self) -> None:
        self._stop_worker()
        self._pcm.clear()
        self._position_ms = 0
        self._set_state("stopped")

    def toggle(self) -> None:
        if self.is_playing():
            self.pause()
        else:
            self.play()

    def is_playing(self) -> bool:
        return self._last_state == "playing" and not self._pause_flag.is_set()

    def position(self) -> int:
        return int(self._position_ms)

    def duration(self) -> int:
        return int(self._duration_ms)

    def set_position(self, ms: int, exact: bool = False) -> None:
        with self._lock:
            self._seek_ms = max(0, int(ms))
        self._position_ms = max(0, int(ms))
        self.position_changed.emit(self._position_ms)

    def seek_relative(self, seconds: float) -> None:
        self.set_position(max(0, self.position() + int(seconds * 1000)), exact=True)

    def volume_percent(self) -> int:
        return int(self._volume_pct)

    def set_volume_percent(self, volume: int) -> None:
        self._volume_pct = max(0, min(200, int(volume)))

    def set_playback_rate(self, rate: float) -> float:
        """Libav sink has no time-stretch; accept and store for UI/MPRIS parity."""
        rate = max(0.25, min(3.0, float(rate)))
        self._playback_rate = rate
        return rate

    def playback_rate(self) -> float:
        return float(getattr(self, "_playback_rate", 1.0) or 1.0)

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)

    def is_muted(self) -> bool:
        return bool(self._muted)

    def source_path(self) -> str:
        return self._source_path

    def clear_last_error(self) -> None:
        pass

    def rebind_video_widget(self, hard: bool = False) -> bool:
        if self.video_widget is not None:
            configure_embed_surface(self.video_widget)
            self.video_widget.update()
        self._video_bound = True
        self.embed_changed.emit(True)
        return True

    def schedule_soft_rebind(self) -> None:
        self.rebind_video_widget(hard=False)

    def prepare_next(self, file_path: str) -> bool:
        if not file_path or not os.path.isfile(file_path):
            return False
        if self._looks_like_video(file_path):
            return False
        self._next_path = file_path
        return True

    def prepared_next_path(self) -> str:
        return self._next_path or ""

    def clear_prepared_next(self) -> None:
        self._next_path = ""

    def promote_prepared_next(self) -> Optional[str]:
        path = self._next_path
        if not path:
            return None
        self._next_path = ""
        self._begin_load(path, start_paused=False)
        return path

    def shutdown(self) -> None:
        if self._poll:
            self._poll.stop()
        self._stop_worker()
        if self._sink is not None:
            try:
                self._sink.stop()
            except Exception:
                pass
            self._sink = None
        self._pcm.close_queue()

    # --- internals ---

    @staticmethod
    def _looks_like_video(path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in {
            ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
            ".mpg", ".mpeg", ".ts", ".m2ts", ".vob", ".hevc", ".h265", ".av1", ".ivf",
        }

    def _set_state(self, state: str) -> None:
        if state != self._last_state:
            self._last_state = state
            self.state_changed.emit(state)

    def _tick(self) -> None:
        self.position_changed.emit(self._position_ms)
        if self._duration_ms:
            self.duration_changed.emit(self._duration_ms)

    def _stop_worker(self) -> None:
        self._stop_flag.set()
        self._pause_flag.clear()
        w = self._worker
        self._worker = None
        if w is not None and w.is_alive():
            w.join(timeout=2.0)

    def _begin_load(self, file_path: str, start_paused: bool) -> None:
        if not file_path or not os.path.isfile(file_path):
            self.error_occurred.emit(f"Libav backend: file not found: {file_path}")
            return
        self._stop_worker()
        self._pcm.clear()
        self._source_path = file_path
        self._position_ms = 0
        self._duration_ms = 0
        self._frame_image = None
        self._load_token += 1
        token = self._load_token
        self._stop_flag.clear()
        if start_paused:
            self._pause_flag.set()
            self._set_state("paused")
        else:
            self._pause_flag.clear()
            self._set_state("playing")
        self._worker = threading.Thread(
            target=self._decode_loop,
            args=(file_path, token),
            name="vox-libav-decode",
            daemon=True,
        )
        self._worker.start()

    def _gain(self) -> float:
        if self._muted:
            return 0.0
        return max(0.0, min(2.0, self._volume_pct / 100.0))

    def _apply_gain_s16(self, data: bytes) -> bytes:
        gain = self._gain()
        if abs(gain - 1.0) < 1e-6:
            return data
        samples = array.array("h")
        samples.frombytes(data)
        for i, s in enumerate(samples):
            v = int(s * gain)
            if v > 32767:
                v = 32767
            elif v < -32768:
                v = -32768
            samples[i] = v
        return samples.tobytes()

    def _emit_frame(self, image: QImage) -> None:
        self._frame_image = image
        if self.video_widget is not None:
            self.video_widget.update()

    def _decode_loop(self, path: str, token: int) -> None:
        import av

        try:
            container = av.open(path)
        except Exception as exc:
            QTimer.singleShot(0, lambda: self.error_occurred.emit(f"Libav open failed: {exc}"))
            return

        try:
            if container.duration and container.duration > 0:
                dur_ms = int(container.duration / av.time_base * 1000)
                self._duration_ms = dur_ms
                QTimer.singleShot(0, lambda d=dur_ms: self.duration_changed.emit(d))

            audio_stream = next(iter(container.streams.audio), None)
            video_stream = next(iter(container.streams.video), None)

            resampler = None
            if audio_stream is not None:
                layout = "stereo" if self._channels >= 2 else "mono"
                resampler = av.AudioResampler(
                    format="s16",
                    layout=layout,
                    rate=self._sample_rate,
                )

            streams = []
            if audio_stream is not None:
                streams.append(audio_stream)
            if video_stream is not None:
                streams.append(video_stream)

            start = time.monotonic()
            media_origin_ms = 0

            def handle_seek():
                nonlocal media_origin_ms, start
                with self._lock:
                    seek = self._seek_ms
                    self._seek_ms = None
                if seek is None:
                    return None
                ts = int(seek / 1000.0 * av.time_base)
                try:
                    container.seek(ts, any_frame=False, backward=True)
                except Exception:
                    try:
                        container.seek(ts)
                    except Exception:
                        return seek
                media_origin_ms = seek
                start = time.monotonic()
                self._pcm.clear()
                return seek

            for packet in container.demux(*streams):
                if self._stop_flag.is_set() or token != self._load_token:
                    break
                while self._pause_flag.is_set() and not self._stop_flag.is_set():
                    time.sleep(0.02)
                    handle_seek()
                if self._stop_flag.is_set() or token != self._load_token:
                    break
                handle_seek()

                try:
                    frames = packet.decode()
                except Exception:
                    continue
                for frame in frames:
                    if self._stop_flag.is_set() or token != self._load_token:
                        break
                    # Clock: prefer audio PTS
                    pts_ms = None
                    try:
                        if frame.pts is not None and frame.time_base is not None:
                            pts_ms = int(float(frame.pts * frame.time_base) * 1000)
                    except Exception:
                        pts_ms = None
                    if pts_ms is not None:
                        self._position_ms = pts_ms
                    else:
                        self._position_ms = media_origin_ms + int((time.monotonic() - start) * 1000)

                    if isinstance(frame, av.AudioFrame) and resampler is not None:
                        for rf in resampler.resample(frame):
                            raw = bytes(rf.planes[0])
                            self._pcm.append(self._apply_gain_s16(raw))
                            # Pace roughly with wall clock buffer fill
                            while (
                                self._pcm.bytesAvailable() > self._sample_rate * self._channels * 2
                                and not self._stop_flag.is_set()
                                and not self._pause_flag.is_set()
                            ):
                                time.sleep(0.005)
                    elif isinstance(frame, av.VideoFrame):
                        try:
                            rgb = frame.reformat(format="rgb24")
                            w, h = rgb.width, rgb.height
                            data = bytes(rgb.planes[0])
                            img = QImage(data, w, h, rgb.planes[0].line_size, QImage.Format.Format_RGB888).copy()
                            QTimer.singleShot(0, lambda i=img: self._emit_frame(i))
                        except Exception:
                            pass

            # natural end
            if not self._stop_flag.is_set() and token == self._load_token:
                if self._next_path:
                    nxt = self._next_path
                    self._next_path = ""
                    QTimer.singleShot(0, lambda p=nxt: self._begin_load(p, start_paused=False))
                else:
                    QTimer.singleShot(0, lambda: self._set_state("ended"))
        except Exception as exc:
            QTimer.singleShot(0, lambda: self.error_occurred.emit(f"Libav decode error: {exc}"))
        finally:
            try:
                container.close()
            except Exception:
                pass
