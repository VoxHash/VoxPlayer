"""Optional plugin hooks — deliberately outside the native playback core.

Plugins may observe shell events and contribute UI actions. They must not
replace demux/decode/output (no second media stack, no engine swaps).

Discovery (in order)::

  1. ``~/.config/voxplayer/plugins/*.py`` (and ``*/plugin.py`` packages)
  2. Entry points group ``voxplayer.plugins`` (pip-installed packages)

Disable with ``VOXPLAYER_PLUGINS=0``.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Sequence


HOOK_NAMES = (
    "on_app_ready",
    "on_track_changed",
    "on_playback_state",
    "on_library_changed",
    "contribute_actions",
)


def plugins_enabled() -> bool:
    raw = os.environ.get("VOXPLAYER_PLUGINS", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def plugins_dir() -> str:
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = xdg if xdg else os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "voxplayer", "plugins")
    os.makedirs(path, exist_ok=True)
    return path


@dataclass
class PluginInfo:
    name: str
    path: str
    source: str  # file | package | entrypoint
    enabled: bool = True
    error: str = ""
    hooks: List[str] = field(default_factory=list)


class PluginHost:
    """Narrow façade exposed to plugins — no engine replacement APIs."""

    def __init__(self, app: Any):
        self._app = app

    def current_path(self) -> str:
        return str(getattr(getattr(self._app, "app_state", None), "last_file", "") or "")

    def volume_percent(self) -> int:
        return int(getattr(getattr(self._app, "app_state", None), "volume", 100) or 100)

    def is_playing(self) -> bool:
        eng = getattr(self._app, "engine", None)
        try:
            return bool(eng and eng.is_playing())
        except Exception:
            return False

    def show_status(self, message: str, timeout_ms: int = 4000) -> None:
        bar = getattr(self._app, "status_bar", None)
        if bar is not None:
            bar.showMessage(str(message), int(timeout_ms))

    def library_paths(self) -> List[str]:
        return list(getattr(self._app, "library_paths", []) or [])


class PluginManager:
    def __init__(self):
        self.host: Optional[PluginHost] = None
        self.plugins: List[PluginInfo] = []
        self._modules: Dict[str, ModuleType] = {}
        self._errors: List[str] = []

    def attach_host(self, app: Any) -> None:
        self.host = PluginHost(app)

    def load_all(self) -> List[PluginInfo]:
        self.plugins = []
        self._modules = {}
        self._errors = []
        if not plugins_enabled():
            return self.plugins
        ensure_example_plugin()
        for path in _discover_plugin_files():
            self._load_file(path)
        for name, ep_value in _discover_entry_points():
            self._load_entrypoint(name, ep_value)
        return self.plugins

    def emit(self, hook: str, *args, **kwargs) -> None:
        if hook not in HOOK_NAMES or not plugins_enabled():
            return
        for name, mod in list(self._modules.items()):
            fn = getattr(mod, hook, None)
            if not callable(fn):
                continue
            try:
                fn(self.host, *args, **kwargs)
            except Exception as exc:
                msg = f"plugin {name}.{hook}: {exc}"
                self._errors.append(msg)
                # Never let a plugin crash the shell
                print(f"[voxplayer plugins] {msg}", file=sys.stderr)

    def collect_actions(self) -> List[Dict[str, Any]]:
        """Return ``[{id, label, callback}]`` from ``contribute_actions`` hooks."""
        actions: List[Dict[str, Any]] = []
        if not plugins_enabled():
            return actions
        for name, mod in list(self._modules.items()):
            fn = getattr(mod, "contribute_actions", None)
            if not callable(fn):
                continue
            try:
                result = fn(self.host)
            except Exception as exc:
                self._errors.append(f"plugin {name}.contribute_actions: {exc}")
                continue
            if not result:
                continue
            for item in result:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or "").strip()
                cb = item.get("callback")
                if not label or not callable(cb):
                    continue
                actions.append(
                    {
                        "id": str(item.get("id") or f"{name}:{label}"),
                        "label": label,
                        "callback": cb,
                        "plugin": name,
                    }
                )
        return actions

    def status_summary(self) -> str:
        if not plugins_enabled():
            return "Plugins disabled (VOXPLAYER_PLUGINS=0)."
        lines = [
            f"Plugin directory: {plugins_dir()}",
            f"Loaded: {len(self._modules)}",
            "",
        ]
        if not self.plugins:
            lines.append("(no plugins found)")
        for info in self.plugins:
            hooks = ", ".join(info.hooks) if info.hooks else "(no hooks)"
            if info.error:
                lines.append(f"• {info.name} [{info.source}] ERROR: {info.error}")
            else:
                lines.append(f"• {info.name} [{info.source}] hooks: {hooks}")
        if self._errors:
            lines.append("")
            lines.append("Recent errors:")
            for err in self._errors[-8:]:
                lines.append(f"  - {err}")
        lines.append("")
        lines.append(
            "Plugins stay out of the native C core — they cannot replace "
            "demux/decode/output."
        )
        return "\n".join(lines)

    def _register(self, name: str, mod: ModuleType, path: str, source: str) -> None:
        hooks = [h for h in HOOK_NAMES if callable(getattr(mod, h, None))]
        info = PluginInfo(name=name, path=path, source=source, hooks=hooks)
        self.plugins.append(info)
        self._modules[name] = mod

    def _load_file(self, path: str) -> None:
        name = os.path.splitext(os.path.basename(path))[0]
        if name.startswith("_") or name == "plugin":
            # package form: dirname is the plugin name
            parent = os.path.basename(os.path.dirname(path))
            if parent and parent not in {".", "plugins"}:
                name = parent
        try:
            spec = importlib.util.spec_from_file_location(
                f"voxplayer_user_plugin_{name}", path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load spec for {path}")
            mod = importlib.util.module_from_spec(spec)
            # Guardrail: refuse modules that try to declare a playback engine
            spec.loader.exec_module(mod)
            if getattr(mod, "PROVIDES_PLAYBACK_ENGINE", False):
                raise RuntimeError(
                    "plugins must not provide a playback engine "
                    "(PROVIDES_PLAYBACK_ENGINE is forbidden)"
                )
            self._register(name, mod, path, "file")
        except Exception as exc:
            self.plugins.append(
                PluginInfo(
                    name=name,
                    path=path,
                    source="file",
                    enabled=False,
                    error=str(exc),
                )
            )
            self._errors.append(f"{name}: {exc}\n{traceback.format_exc()}")

    def _load_entrypoint(self, name: str, value: str) -> None:
        try:
            modname, _, attr = value.partition(":")
            mod = importlib.import_module(modname)
            if attr:
                obj = mod
                for part in attr.split("."):
                    obj = getattr(obj, part)
                if isinstance(obj, ModuleType):
                    mod = obj
                else:
                    # treat as module-like namespace object
                    wrapper = ModuleType(f"voxplayer_ep_{name}")
                    for hook in HOOK_NAMES:
                        if callable(getattr(obj, hook, None)):
                            setattr(wrapper, hook, getattr(obj, hook))
                        elif callable(obj) and hook == "on_app_ready":
                            setattr(wrapper, hook, obj)
                    mod = wrapper
            if getattr(mod, "PROVIDES_PLAYBACK_ENGINE", False):
                raise RuntimeError("plugins must not provide a playback engine")
            self._register(name, mod, value, "entrypoint")
        except Exception as exc:
            self.plugins.append(
                PluginInfo(
                    name=name,
                    path=value,
                    source="entrypoint",
                    enabled=False,
                    error=str(exc),
                )
            )


def _discover_plugin_files() -> List[str]:
    root = plugins_dir()
    found: List[str] = []
    try:
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            if name.endswith(".py") and not name.startswith("_"):
                found.append(path)
            elif os.path.isdir(path) and not name.startswith("_"):
                candidate = os.path.join(path, "plugin.py")
                if os.path.isfile(candidate):
                    found.append(candidate)
    except OSError:
        pass
    return found


def _discover_entry_points() -> List[tuple]:
    out: List[tuple] = []
    try:
        from importlib.metadata import entry_points
    except ImportError:
        return out
    try:
        eps = entry_points()
        # Python 3.10+ SelectableGroups; 3.8/3.9 dict-like
        if hasattr(eps, "select"):
            group = eps.select(group="voxplayer.plugins")
        else:
            group = eps.get("voxplayer.plugins", [])  # type: ignore[arg-type]
        for ep in group:
            out.append((ep.name, ep.value))
    except Exception:
        pass
    return out


def ensure_example_plugin() -> None:
    """Write a sample observer plugin once so the hooks directory is self-documenting."""
    path = os.path.join(plugins_dir(), "example_nowplaying_log.py")
    if os.path.isfile(path):
        return
    body = '''\
"""Example VoxPlayer plugin — logs track changes (shell-side only).

Copy/edit this file or add new ``*.py`` modules next to it.
Hooks: on_app_ready, on_track_changed, on_playback_state, on_library_changed,
contribute_actions. Do not set PROVIDES_PLAYBACK_ENGINE.
"""

from __future__ import annotations

import os
import time

_LOG = os.path.join(os.path.expanduser("~"), ".cache", "voxplayer", "plugin_nowplaying.log")


def _append(line: str) -> None:
    os.makedirs(os.path.dirname(_LOG), exist_ok=True)
    with open(_LOG, "a", encoding="utf-8") as fh:
        fh.write(line.rstrip() + "\\n")


def on_app_ready(host) -> None:
    _append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} ready plugins_dir ok")


def on_track_changed(host, path, meta=None):
    title = ""
    if isinstance(meta, dict):
        title = str(meta.get("title") or "")
    _append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} track {path} {title}".rstrip())


def on_playback_state(host, state: str) -> None:
    _append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} state {state}")


def contribute_actions(host):
    def _show_log(_checked=False):
        host.show_status(f"Now-playing log: {_LOG}", 5000)
        try:
            import webbrowser
            from PyQt6.QtCore import QUrl
            webbrowser.open(QUrl.fromLocalFile(_LOG).toString())
        except Exception:
            pass

    return [{"id": "example.open_log", "label": "Open now-playing plugin log", "callback": _show_log}]
'''
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        readme = os.path.join(plugins_dir(), "README.txt")
        if not os.path.isfile(readme):
            with open(readme, "w", encoding="utf-8") as fh:
                fh.write(
                    "VoxPlayer plugins (optional)\n"
                    "============================\n"
                    "Place *.py modules here. They run in the PyQt6 shell only.\n"
                    "They cannot replace the native C media core.\n"
                    "Disable all plugins: VOXPLAYER_PLUGINS=0\n"
                    "Also discoverable via entry point group: voxplayer.plugins\n"
                )
        manifest = os.path.join(plugins_dir(), "hooks.json")
        if not os.path.isfile(manifest):
            with open(manifest, "w", encoding="utf-8") as fh:
                json.dump({"hooks": list(HOOK_NAMES)}, fh, indent=2)
                fh.write("\n")
    except OSError:
        pass
