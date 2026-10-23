"""Group library paths by local metadata facets for browse UI."""

from __future__ import annotations

import os
import re
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"}
AUDIO_EXT = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus"}

_SEASON_RE = re.compile(
    r"(?:^|[.\s_\-])(?:S|Season[\s._-]*)(\d{1,2})(?:[.\s_\-]*E|x)(\d{1,3})",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"(?:^|[.\s_\-(\[])((?:19|20)\d{2})(?:[.\s_\-)\]]|$)")


def media_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXT:
        return "Video"
    if ext in AUDIO_EXT:
        return "Audio"
    return "Other"


def infer_year(path: str, meta_year: str = "") -> str:
    if meta_year and str(meta_year).strip():
        return str(meta_year).strip()[:4]
    m = _YEAR_RE.search(os.path.basename(path))
    return m.group(1) if m else "Unknown"


def infer_show_season(path: str) -> Optional[Tuple[str, str]]:
    """Return (show_title, season_label) for TV-like filenames, else None."""
    base = os.path.splitext(os.path.basename(path))[0]
    m = _SEASON_RE.search(base)
    if not m:
        return None
    season = f"Season {int(m.group(1))}"
    show = base[: m.start()].strip(" ._-")
    show = re.sub(r"[\._]+", " ", show).strip() or "Unknown Show"
    return show, season


def group_library(
    paths: Iterable[str],
    meta_by_path: Optional[Dict[str, object]] = None,
) -> Dict[str, Dict[str, List[str]]]:
    """
    Build nested facet maps:
      year / genre / artist (audio) · movies / tv (video)
    Each value is { bucket_label: [paths...] }.
    """
    meta_by_path = meta_by_path or {}
    years: Dict[str, List[str]] = defaultdict(list)
    genres: Dict[str, List[str]] = defaultdict(list)
    artists: Dict[str, List[str]] = defaultdict(list)
    movies: Dict[str, List[str]] = defaultdict(list)
    tv: Dict[str, List[str]] = defaultdict(list)

    for path in paths:
        if not path:
            continue
        meta = meta_by_path.get(path)
        artist = getattr(meta, "artist", "") or ""
        genre = getattr(meta, "genre", "") or ""
        year = infer_year(path, getattr(meta, "year", "") or "")
        mtype = media_type(path)
        title = getattr(meta, "title", "") or os.path.splitext(os.path.basename(path))[0]

        if mtype == "Audio":
            years[year].append(path)
            genres[(genre.strip() or "Unknown")].append(path)
            artists[(artist.strip() or "Unknown Artist")].append(path)
        elif mtype == "Video":
            show_season = infer_show_season(path)
            if show_season:
                show, season = show_season
                tv[f"{show} · {season}"].append(path)
            else:
                movies[f"{year} · {title}"].append(path)

    def _sorted_buckets(src: Dict[str, List[str]], reverse: bool = False) -> Dict[str, List[str]]:
        keys = sorted(src.keys(), reverse=reverse, key=lambda k: (k == "Unknown", k.lower() if isinstance(k, str) else k))
        return {k: src[k] for k in keys}

    return {
        "year": _sorted_buckets(years, reverse=True),
        "genre": _sorted_buckets(genres),
        "artist": _sorted_buckets(artists),
        "movies": _sorted_buckets(movies, reverse=True),
        "tv": _sorted_buckets(tv),
    }
