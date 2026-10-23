"""VoxPlayer visual identity — unique dark shell, not a clone of any third-party brand."""

# Deep charcoal surfaces with warm ember accent (never industry-green streaming accents).
COLORS = {
    "bg_app": "#0B0F14",
    "bg_panel": "#121820",
    "bg_elevated": "#1A2330",
    "bg_hover": "#243044",
    "bg_input": "#0F141C",
    "border": "#2A3548",
    "border_soft": "#1E2836",
    "text": "#F2F4F7",
    "text_secondary": "#9AA6B8",
    "text_muted": "#6B7789",
    "accent": "#FF8A3D",
    "accent_hover": "#FFB070",
    "accent_pressed": "#E06E28",
    "accent_soft": "rgba(255, 138, 61, 0.18)",
    "focus": "#3DDCFF",
    "danger": "#FF6B6B",
    "success": "#5AD67D",
    "transport": "#0E141C",
    "rail": "#0D1219",
}

# Prefer distinctive desktop fonts already common on Linux/Windows/macOS.
FONT_UI = '"Segoe UI", "Ubuntu", "Noto Sans", "Cantarell", sans-serif'
FONT_DISPLAY = '"Segoe UI Semibold", "Ubuntu", "Noto Sans", sans-serif'
FONT_MONO = '"Cascadia Code", "JetBrains Mono", "Consolas", "Ubuntu Mono", monospace'


def app_stylesheet() -> str:
    c = COLORS
    return f"""
    QMainWindow, QDialog {{
        background-color: {c['bg_app']};
        color: {c['text']};
        font-family: {FONT_UI};
        font-size: 13px;
    }}
    QWidget#ShellRoot {{
        background-color: {c['bg_app']};
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
        background: {c['bg_elevated']};
        border: 1px solid {c['border']};
        border-radius: 16px;
        color: {c['text']};
        padding: 6px 14px;
        font-size: 12px;
    }}
    QPushButton#Chip:hover {{
        border-color: {c['accent']};
        color: {c['accent']};
    }}
    QPushButton#Chip[active="true"] {{
        background: {c['accent']};
        border-color: {c['accent']};
        color: #1A1208;
        font-weight: 600;
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
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
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
        color: {c['text_muted']};
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
