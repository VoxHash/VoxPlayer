"""VoxPlayer visual identity — unique dark shell, not a clone of any third-party brand.

Bundled palettes plus optional user theme packs under::

    ~/.config/voxplayer/themes/<id>.json
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Dict, List, Optional, Tuple

# Deep charcoal surfaces with warm ember accent (never industry-green streaming accents).
# text_muted / border tuned for WCAG 2.2 AA (≥4.5:1 text, ≥3:1 non-text) on bg_app.
_EMBER: Dict[str, str] = {
    "bg_app": "#0B0F14",
    "bg_panel": "#121820",
    "bg_elevated": "#1A2330",
    "bg_hover": "#243044",
    "bg_input": "#0F141C",
    "border": "#6A7588",
    "border_soft": "#4A5568",
    "text": "#F2F4F7",
    "text_secondary": "#B0BBCB",
    "text_muted": "#8A96A8",
    "accent": "#FF8A3D",
    "accent_hover": "#FFB070",
    "accent_pressed": "#E06E28",
    "accent_soft": "rgba(255, 138, 61, 0.22)",
    "focus": "#3DDCFF",
    "danger": "#FF6B6B",
    "success": "#5AD67D",
    "transport": "#0E141C",
    "rail": "#0D1219",
}

# Cool midnight blue with cyan accent (distinct from ember).
_MIDNIGHT: Dict[str, str] = {
    "bg_app": "#070B12",
    "bg_panel": "#0E1520",
    "bg_elevated": "#162032",
    "bg_hover": "#1E2C42",
    "bg_input": "#0A1018",
    "border": "#6B7C96",
    "border_soft": "#4A5A72",
    "text": "#E8EEF7",
    "text_secondary": "#A8B8D0",
    "text_muted": "#8A9BB4",
    "accent": "#3DB8FF",
    "accent_hover": "#7AD0FF",
    "accent_pressed": "#2A8FCC",
    "accent_soft": "rgba(61, 184, 255, 0.22)",
    "focus": "#FFC857",
    "danger": "#FF6B6B",
    "success": "#5AD67D",
    "transport": "#0A1018",
    "rail": "#090E16",
}

# Neutral slate with soft gold accent.
_SLATE: Dict[str, str] = {
    "bg_app": "#101214",
    "bg_panel": "#171A1E",
    "bg_elevated": "#22262C",
    "bg_hover": "#2C323A",
    "bg_input": "#14171A",
    "border": "#707880",
    "border_soft": "#505860",
    "text": "#F0F1F3",
    "text_secondary": "#B4B9C2",
    "text_muted": "#9098A2",
    "accent": "#D4A05A",
    "accent_hover": "#E8C07A",
    "accent_pressed": "#B8843F",
    "accent_soft": "rgba(212, 160, 90, 0.22)",
    "focus": "#7EC8E3",
    "danger": "#E57373",
    "success": "#81C784",
    "transport": "#121518",
    "rail": "#0E1012",
}

# Near-black graphite with coral accent (not purple / not cream).
_GRAPHITE: Dict[str, str] = {
    "bg_app": "#0A0A0A",
    "bg_panel": "#141414",
    "bg_elevated": "#1E1E1E",
    "bg_hover": "#2A2A2A",
    "bg_input": "#121212",
    "border": "#707070",
    "border_soft": "#505050",
    "text": "#F5F5F5",
    "text_secondary": "#C0C0C0",
    "text_muted": "#9A9A9A",
    "accent": "#FF6F61",
    "accent_hover": "#FF948A",
    "accent_pressed": "#E05548",
    "accent_soft": "rgba(255, 111, 97, 0.22)",
    "focus": "#64B5F6",
    "danger": "#EF5350",
    "success": "#66BB6A",
    "transport": "#101010",
    "rail": "#0C0C0C",
}

BUNDLED_THEMES: Dict[str, Dict[str, str]] = {
    "ember": _EMBER,
    "midnight": _MIDNIGHT,
    "slate": _SLATE,
    "graphite": _GRAPHITE,
}

THEME_LABELS: Dict[str, str] = {
    "ember": "Ember (default)",
    "midnight": "Midnight",
    "slate": "Slate",
    "graphite": "Graphite",
}

# Live palette — mutated in place so `from theme import COLORS` stays current.
COLORS: Dict[str, str] = deepcopy(_EMBER)
ACTIVE_THEME_ID = "ember"
HIGH_CONTRAST = False

# Prefer distinctive desktop fonts already common on Linux/Windows/macOS.
FONT_UI = '"Segoe UI", "Ubuntu", "Noto Sans", "Cantarell", sans-serif'
FONT_DISPLAY = '"Segoe UI Semibold", "Ubuntu", "Noto Sans", sans-serif'
FONT_MONO = '"Cascadia Code", "JetBrains Mono", "Consolas", "Ubuntu Mono", monospace'

_COLOR_KEYS = tuple(_EMBER.keys())


def user_themes_dir() -> str:
    """``~/.config/voxplayer/themes`` (XDG) — user JSON packs live here."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = xdg if xdg else os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "voxplayer", "themes")
    os.makedirs(path, exist_ok=True)
    return path


def ensure_example_user_theme() -> None:
    """Write a sample pack once so users see the expected JSON shape."""
    sample = os.path.join(user_themes_dir(), "example-ocean.json")
    if os.path.isfile(sample):
        return
    ocean = deepcopy(_MIDNIGHT)
    ocean["accent"] = "#2DD4BF"
    ocean["accent_hover"] = "#5EEAD4"
    ocean["accent_pressed"] = "#14B8A6"
    ocean["accent_soft"] = "rgba(45, 212, 191, 0.18)"
    payload = {
        "id": "example-ocean",
        "name": "Ocean (example user pack)",
        "colors": ocean,
    }
    try:
        with open(sample, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
    except OSError:
        pass


def _normalize_colors(raw: dict) -> Optional[Dict[str, str]]:
    if not isinstance(raw, dict):
        return None
    out = deepcopy(_EMBER)
    for key in _COLOR_KEYS:
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()
    return out


def _load_user_pack(path: str) -> Optional[Tuple[str, str, Dict[str, str]]]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    colors = _normalize_colors(data.get("colors") or data)
    if not colors:
        return None
    stem = os.path.splitext(os.path.basename(path))[0]
    tid = str(data.get("id") or stem).strip() or stem
    name = str(data.get("name") or tid).strip() or tid
    return tid, name, colors


def list_themes() -> List[Tuple[str, str, str]]:
    """Return ``(id, label, source)`` — source is ``bundled`` or ``user``."""
    ensure_example_user_theme()
    out: List[Tuple[str, str, str]] = []
    for tid, label in THEME_LABELS.items():
        out.append((tid, label, "bundled"))
    for name in sorted(os.listdir(user_themes_dir())):
        if not name.endswith(".json") or name.startswith("."):
            continue
        packed = _load_user_pack(os.path.join(user_themes_dir(), name))
        if not packed:
            continue
        tid, label, _ = packed
        if tid in BUNDLED_THEMES:
            tid = f"user-{tid}"
        out.append((tid, f"{label} (user)", "user"))
    return out


def resolve_palette(theme_id: str) -> Dict[str, str]:
    tid = (theme_id or "ember").strip() or "ember"
    if tid in BUNDLED_THEMES:
        return deepcopy(BUNDLED_THEMES[tid])
    # user- prefix or raw filename stem
    raw_id = tid[5:] if tid.startswith("user-") else tid
    path = os.path.join(user_themes_dir(), f"{raw_id}.json")
    if not os.path.isfile(path):
        # try any pack whose id matches
        for name in os.listdir(user_themes_dir()):
            if not name.endswith(".json"):
                continue
            packed = _load_user_pack(os.path.join(user_themes_dir(), name))
            if packed and packed[0] == raw_id:
                return deepcopy(packed[2])
        return deepcopy(_EMBER)
    packed = _load_user_pack(path)
    return deepcopy(packed[2]) if packed else deepcopy(_EMBER)


def _hex_to_rgb(h: str) -> Tuple[float, float, float]:
    h = (h or "").lstrip("#")
    if len(h) != 6:
        return 0.0, 0.0, 0.0
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def _linearize(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG relative luminance contrast ratio between two ``#RRGGBB`` colors."""
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _high_contrast_overlay(palette: Dict[str, str]) -> Dict[str, str]:
    """Boost muted text and borders further for the optional high-contrast mode."""
    out = deepcopy(palette)
    out["text"] = "#FFFFFF"
    out["text_secondary"] = "#E8ECF2"
    out["text_muted"] = "#C8D0DC"
    out["border"] = "#A0AAB8"
    out["border_soft"] = "#808A98"
    # Keep accent readable; brighten focus ring
    out["focus"] = "#FFE566"
    return out


def apply_theme_id(theme_id: str) -> str:
    """Apply palette into live ``COLORS``. Returns the resolved theme id."""
    global ACTIVE_THEME_ID
    tid = (theme_id or "ember").strip() or "ember"
    if tid not in BUNDLED_THEMES and not tid.startswith("user-"):
        # Prefer explicit user- prefix when matching a user pack id.
        for cand_id, _label, source in list_themes():
            if source == "user" and (
                cand_id == tid or cand_id == f"user-{tid}" or cand_id.endswith(tid)
            ):
                tid = cand_id
                break
    palette = resolve_palette(tid)
    if HIGH_CONTRAST:
        palette = _high_contrast_overlay(palette)
    COLORS.clear()
    COLORS.update(palette)
    ACTIVE_THEME_ID = tid
    return ACTIVE_THEME_ID


def set_high_contrast(enabled: bool) -> bool:
    """Toggle high-contrast overlay and re-apply the active theme. Returns new state."""
    global HIGH_CONTRAST
    HIGH_CONTRAST = bool(enabled)
    apply_theme_id(ACTIVE_THEME_ID)
    return HIGH_CONTRAST


def accessibility_contrast_report(theme_id: Optional[str] = None) -> List[str]:
    """Human-readable AA checks for the (optionally high-contrast) palette."""
    tid = theme_id or ACTIVE_THEME_ID
    base = resolve_palette(tid)
    pal = _high_contrast_overlay(base) if HIGH_CONTRAST else base
    bg = pal["bg_app"]
    lines = [
        f"Theme: {tid}" + (" (high contrast)" if HIGH_CONTRAST else ""),
        f"bg_app: {bg}",
        "",
        "Text vs bg_app (need ≥4.5:1 AA):",
    ]
    for key in ("text", "text_secondary", "text_muted", "accent", "focus"):
        ratio = contrast_ratio(pal[key], bg)
        ok = "PASS" if ratio >= 4.5 else "FAIL"
        lines.append(f"  {key}: {ratio:.2f}:1  [{ok}]")
    lines.append("")
    lines.append("Non-text vs bg_app (need ≥3:1):")
    for key in ("border", "border_soft"):
        ratio = contrast_ratio(pal[key], bg)
        ok = "PASS" if ratio >= 3.0 else "FAIL"
        lines.append(f"  {key}: {ratio:.2f}:1  [{ok}]")
    return lines


def app_stylesheet() -> str:
    c = COLORS
    focus_w = 3 if HIGH_CONTRAST else 2
    return f"""
    QMainWindow, QDialog {{
        background-color: {c['bg_app']};
        color: {c['text']};
        font-family: {FONT_UI};
        font-size: {'14px' if HIGH_CONTRAST else '13px'};
    }}
    QWidget#ShellRoot {{
        background-color: {c['bg_app']};
    }}
    /* WCAG-oriented keyboard focus — visible 2–3px ring (SC 2.4.7 / 2.4.13) */
    QPushButton:focus, QLineEdit:focus, QSlider:focus, QListWidget:focus,
    QMenuBar:focus, QAbstractButton:focus {{
        outline: {focus_w}px solid {c['focus']};
        outline-offset: 2px;
    }}
    QPushButton:focus {{
        border: {focus_w}px solid {c['focus']};
    }}
    QWidget#LeftRail, QWidget#NowPlayingPanel, QWidget#TransportBar {{
        background-color: {c['bg_panel']};
        border: none;
    }}
    QWidget#LeftRail {{
        background-color: {c['rail']};
        border-right: 1px solid {c['border_soft']};
    }}
    QWidget#NowPlayingPanel {{
        border-left: 1px solid {c['border_soft']};
    }}
    QWidget#TransportBar {{
        background-color: {c['transport']};
        border-top: 1px solid {c['border']};
    }}
    QWidget#CenterStage {{
        background-color: {c['bg_app']};
    }}
    QLabel#BrandMark {{
        color: {c['accent']};
        font-family: {FONT_DISPLAY};
        font-size: 15px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    QLabel#SectionTitle {{
        color: {c['text']};
        font-family: {FONT_DISPLAY};
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel#SectionLink {{
        color: {c['text_secondary']};
        font-size: 12px;
    }}
    QLabel#MetaPrimary {{
        color: {c['text']};
        font-size: 16px;
        font-weight: 600;
    }}
    QLabel#MetaSecondary {{
        color: {c['text_secondary']};
        font-size: 13px;
    }}
    QLabel#MetaMuted {{
        color: {c['text_muted']};
        font-size: 12px;
    }}
    QPushButton#RailButton {{
        background: transparent;
        border: none;
        border-radius: 8px;
        color: {c['text_secondary']};
        padding: 10px;
        font-size: 16px;
    }}
    QPushButton#RailButton:hover {{
        background: {c['bg_hover']};
        color: {c['text']};
    }}
    QPushButton#RailButton[active="true"] {{
        background: {c['accent_soft']};
        color: {c['accent']};
    }}
    QPushButton#Chip {{
        background: transparent;
        border: none;
        border-radius: 8px;
        color: {c['text_secondary']};
        padding: 6px 12px;
        font-size: 12px;
    }}
    QPushButton#Chip:hover {{
        color: {c['text']};
        background: {c['bg_hover']};
    }}
    QPushButton#Chip[active="true"] {{
        background: transparent;
        border: none;
        border-bottom: 2px solid {c['accent']};
        border-radius: 0;
        color: {c['accent']};
        font-weight: 600;
    }}
    QPushButton#FilterTab {{
        background: transparent;
        border: none;
        border-radius: 0;
        border-bottom: 2px solid transparent;
        color: {c['text_secondary']};
        padding: 8px 12px 6px 12px;
        font-size: 12px;
        font-weight: 500;
    }}
    QPushButton#FilterTab:hover {{
        color: {c['text']};
        background: {c['accent_soft']};
        border-radius: 8px;
        border-bottom: 2px solid transparent;
    }}
    QPushButton#FilterTab[active="true"] {{
        color: {c['accent']};
        background: transparent;
        border-bottom: 2px solid {c['accent']};
        font-weight: 600;
    }}
    QPushButton#LibraryNav {{
        background: transparent;
        border: none;
        border-radius: 0;
        color: {c['text_secondary']};
        padding: 4px 10px 6px 10px;
        font-family: {FONT_DISPLAY};
        font-size: 15px;
        font-weight: 600;
        letter-spacing: 0.2px;
    }}
    QPushButton#LibraryNav:hover {{
        color: {c['text']};
    }}
    QPushButton#LibraryNav[active="true"] {{
        color: {c['text']};
        border-bottom: 2px solid {c['accent']};
    }}
    QPushButton#FilterIcon {{
        background: transparent;
        border: none;
        border-radius: 8px;
        color: {c['text_secondary']};
        font-size: 14px;
        padding: 4px;
    }}
    QPushButton#FilterIcon:hover {{
        color: {c['text']};
        background: {c['bg_hover']};
    }}
    QPushButton#FilterIcon[active="true"] {{
        color: {c['accent']};
        background: {c['accent_soft']};
    }}
    QPushButton#TransportPrimary {{
        background: {c['text']};
        border: none;
        border-radius: 18px;
        color: {c['bg_app']};
        font-size: 14px;
        font-weight: 700;
        min-width: 36px;
        min-height: 36px;
    }}
    QPushButton#TransportPrimary:hover {{
        background: {c['accent']};
        color: #1A1208;
    }}
    QPushButton#TransportGhost {{
        background: transparent;
        border: none;
        border-radius: 8px;
        color: {c['text_secondary']};
        font-size: 14px;
        padding: 6px 8px;
    }}
    QPushButton#TransportGhost:hover {{
        color: {c['text']};
        background: {c['bg_hover']};
    }}
    QPushButton#NpIconBtn {{
        background: transparent;
        border: none;
        border-radius: 6px;
        color: {c['text_secondary']};
        font-size: 14px;
        padding: 2px;
    }}
    QPushButton#NpIconBtn:hover {{
        background: {c['bg_hover']};
        color: {c['accent']};
    }}
    QLineEdit#SearchField {{
        background: {c['bg_input']};
        border: 1px solid {c['border']};
        border-radius: 20px;
        color: {c['text']};
        padding: 8px 16px;
        font-size: 13px;
        selection-background-color: {c['accent']};
    }}
    QLineEdit#SearchField:focus {{
        border-color: {c['focus']};
    }}
    QSlider::groove:horizontal {{
        border: none;
        height: 4px;
        background: {c['border']};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {c['accent']};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {c['text']};
        border: none;
        width: 12px;
        height: 12px;
        margin: -4px 0;
        border-radius: 6px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {c['accent']};
    }}
    QListWidget#LibraryList, QListWidget#QueueList {{
        background: transparent;
        border: none;
        outline: none;
        color: {c['text']};
    }}
    QListWidget#LibraryList::item, QListWidget#QueueList::item {{
        padding: 8px 10px;
        border-radius: 8px;
        margin: 1px 4px;
    }}
    QListWidget#LibraryList::item:hover, QListWidget#QueueList::item:hover {{
        background: {c['bg_hover']};
    }}
    QListWidget#LibraryList::item:selected, QListWidget#QueueList::item:selected {{
        background: {c['accent_soft']};
        color: {c['accent']};
    }}
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollArea#LibraryScroll, QListWidget#LibraryList, QListWidget#QueueList {{
        background: transparent;
        border: none;
    }}
    /* Wider, higher-contrast scrollbars — easier to see and grab on dark UI */
    QScrollBar:vertical {{
        background: {c['bg_input']};
        width: 14px;
        margin: 2px;
        border-radius: 7px;
        border: 1px solid {c['border_soft']};
    }}
    QScrollBar::handle:vertical {{
        background: {c['text_muted']};
        border-radius: 6px;
        min-height: 36px;
        margin: 2px;
        border: 1px solid {c['border']};
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['accent']};
        border-color: {c['accent_hover']};
    }}
    QScrollBar::handle:vertical:pressed {{
        background: {c['accent_pressed']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
        width: 0;
        background: none;
        border: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}
    QScrollBar:horizontal {{
        background: {c['bg_input']};
        height: 14px;
        margin: 2px;
        border-radius: 7px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['text_muted']};
        border-radius: 6px;
        min-width: 36px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c['accent']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
        height: 0;
    }}
    QMenuBar {{
        background-color: {c['bg_panel']};
        color: {c['text']};
        border-bottom: 1px solid {c['border_soft']};
        padding: 2px;
    }}
    QMenuBar::item:selected {{
        background: {c['bg_hover']};
        border-radius: 4px;
    }}
    QMenu {{
        background-color: {c['bg_elevated']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 4px;
    }}
    QMenu::item:selected {{
        background: {c['accent_soft']};
        color: {c['accent']};
    }}
    QStatusBar {{
        background: {c['bg_panel']};
        color: {c['text_secondary']};
        border-top: 1px solid {c['border_soft']};
    }}
    QMessageBox {{
        background-color: {c['bg_elevated']};
        color: {c['text']};
    }}
    QVideoWidget {{
        background-color: #000000;
        border: none;
        border-radius: 8px;
    }}
    QFrame#MediaCard {{
        background: {c['bg_elevated']};
        border: 1px solid {c['border_soft']};
        border-radius: 12px;
    }}
    QFrame#MediaCard:hover {{
        border-color: {c['accent']};
        background: {c['bg_hover']};
    }}
    """
