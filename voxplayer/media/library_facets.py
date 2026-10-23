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
    stats_by_path: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Dict[str, List[str]]]:
    """
    Build nested facet maps:
      year / genre / artist / album (audio) · movies / tv (video)
      recently / never / most_played (from local play stats)
    Each value is { bucket_label: [paths...] }.
    """
    meta_by_path = meta_by_path or {}
    stats_by_path = stats_by_path or {}
    years: Dict[str, List[str]] = defaultdict(list)
    genres: Dict[str, List[str]] = defaultdict(list)
    artists: Dict[str, List[str]] = defaultdict(list)
    albums: Dict[str, List[str]] = defaultdict(list)
    movies: Dict[str, List[str]] = defaultdict(list)
    tv: Dict[str, List[str]] = defaultdict(list)
    never: List[str] = []
    played: List[Tuple[float, str]] = []  # (last_played, path)
    counted: List[Tuple[int, str]] = []  # (play_count, path)

    path_list = [p for p in paths if p]
    for path in path_list:
        meta = meta_by_path.get(path)
        artist = getattr(meta, "artist", "") or ""
        album = getattr(meta, "album", "") or ""
        genre = getattr(meta, "genre", "") or ""
        year = infer_year(path, getattr(meta, "year", "") or "")
        mtype = media_type(path)
        title = getattr(meta, "title", "") or os.path.splitext(os.path.basename(path))[0]

        if mtype == "Audio":
            years[year].append(path)
            genres[(genre.strip() or "Unknown")].append(path)
            artists[(artist.strip() or "Unknown Artist")].append(path)
            alb = album.strip()
            if alb:
                label = f"{artist.strip() or 'Unknown'} · {alb}" if artist.strip() else alb
            else:
                label = "Unknown Album"
            albums[label].append(path)
        elif mtype == "Video":
            show_season = infer_show_season(path)
            if show_season:
                show, season = show_season
                tv[f"{show} · {season}"].append(path)
            else:
                movies[f"{year} · {title}"].append(path)

        abs_key = os.path.abspath(path)
        st = stats_by_path.get(abs_key) or stats_by_path.get(path) or {}
        try:
            count = int(float(st.get("play_count") or 0))
        except (TypeError, ValueError):
            count = 0
        try:
            last = float(st.get("last_played") or 0.0)
        except (TypeError, ValueError):
            last = 0.0
        if count <= 0 and last <= 0:
            never.append(path)
        else:
            played.append((last, path))
            counted.append((count, path))

    def _sorted_buckets(src: Dict[str, List[str]], reverse: bool = False) -> Dict[str, List[str]]:
        keys = sorted(
            src.keys(),
            reverse=reverse,
            key=lambda k: (k.startswith("Unknown"), k.lower() if isinstance(k, str) else k),
        )
        return {k: src[k] for k in keys}

    played.sort(key=lambda t: t[0], reverse=True)
    recently_map: Dict[str, List[str]] = {}
    if played:
        recently_map["Recently played"] = [p for _, p in played[:48]]
    never_map: Dict[str, List[str]] = {}
    if never:
        never_map["Never played"] = sorted(never, key=lambda p: os.path.basename(p).lower())
    counted.sort(key=lambda t: (-t[0], os.path.basename(t[1]).lower()))
    most_map: Dict[str, List[str]] = {}
    if counted:
        # Bucket by play-count tiers for browse chips
        tiers: Dict[str, List[str]] = defaultdict(list)
        for count, path in counted:
            if count >= 10:
                tiers["10+ plays"].append(path)
            elif count >= 3:
                tiers["3–9 plays"].append(path)
            else:
                tiers["1–2 plays"].append(path)
        for label in ("10+ plays", "3–9 plays", "1–2 plays"):
            if tiers.get(label):
                most_map[label] = tiers[label]

    return {
        "year": _sorted_buckets(years, reverse=True),
        "genre": _sorted_buckets(genres),
        "artist": _sorted_buckets(artists),
        "album": _sorted_buckets(albums),
        "movies": _sorted_buckets(movies, reverse=True),
        "tv": _sorted_buckets(tv),
        "recently": recently_map,
        "never": never_map,
        "most_played": most_map,
    }
