"""
Online / local metadata enrichment.

Strategy (best-effort, graceful fallback):
1. ffprobe / mutagen embedded tags
2. Filename heuristics (Artist - Title)
3. MusicBrainz recording search (no API key; identify User-Agent)
4. Optional AcoustID fingerprint when ACOUSTID_API_KEY is set
5. Cover Art Archive when a MusicBrainz release group / release MBID is known
6. Optional TMDB for video titles when TMDB_API_KEY is set

Keys stay in the environment / local .env (gitignored) — never commit them.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import requests

USER_AGENT = "VoxPlayer/1.1.1 (https://github.com/VoxHash/VoxPlayer; contact@voxhash.dev)"
MB_BASE = "https://musicbrainz.org/ws/2"
CAA_BASE = "https://coverartarchive.org"
ACOUSTID_LOOKUP = "https://api.acoustid.org/v2/lookup"
TMDB_SEARCH = "https://api.themoviedb.org/3/search/multi"


@dataclass
class MediaMetadata:
    path: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    year: str = ""
    genre: str = ""
    cover_path: str = ""
    source: str = "local"
    extra: Dict[str, Any] = field(default_factory=dict)

    def display_title(self) -> str:
        return self.title or (os.path.basename(self.path) if self.path else "Unknown")

    def display_subtitle(self) -> str:
        parts = [p for p in (self.artist, self.album, self.year) if p]
        if parts:
            return " · ".join(parts)
        if self.path:
            return os.path.dirname(self.path)
        return ""


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return s


def _ffprobe_tags(path: str) -> Dict[str, str]:
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
        if proc.returncode != 0 or not proc.stdout:
            return {}
        data = json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}

    tags: Dict[str, str] = {}
    fmt = data.get("format") or {}
    for k, v in (fmt.get("tags") or {}).items():
        tags[str(k).lower()] = str(v)
    for stream in data.get("streams") or []:
        for k, v in (stream.get("tags") or {}).items():
            tags.setdefault(str(k).lower(), str(v))
    return tags


def _mutagen_tags(path: str) -> Dict[str, str]:
    try:
        from mutagen import File as MutagenFile  # type: ignore
    except ImportError:
        return {}
    try:
        audio = MutagenFile(path, easy=True)
        if not audio or not getattr(audio, "tags", None):
            return {}
        out = {}
        for key in ("title", "artist", "album", "date", "genre"):
            val = audio.tags.get(key)
            if val:
                out[key] = val[0] if isinstance(val, list) else str(val)
        return out
    except Exception:
        return {}


def _strip_release_noise(text: str) -> str:
    """Remove YouTube / rip noise so MusicBrainz queries stay useful."""
    cleaned = re.sub(
        r"(?i)\b(official\s+video|official\s+audio|lyrics?|lyric\s+video|"
        r"audio|mv|music\s+video|visualizer|hd|hq|4k|1080p|720p|"
        r"\d+\s*kbit[_\s-]?\w+|feat\.?|ft\.?)\b",
        " ",
        text or "",
    )
    cleaned = re.sub(r"[\[\(\{].*?[\]\)\}]", " ", cleaned)
    cleaned = re.sub(r"[_\|/]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_.\"'")
    return cleaned


def _parse_filename(path: str) -> Tuple[str, str]:
    name = os.path.splitext(os.path.basename(path))[0]
    cleaned = _strip_release_noise(name)
    # Artist - Title
    if " - " in cleaned:
        left, right = cleaned.split(" - ", 1)
        return left.strip(), right.strip()
    return "", cleaned


def _musicbrainz_search(artist: str, title: str, min_score: int = 85) -> Optional[Dict[str, Any]]:
    if not title:
        return None
    query_parts = [f'recording:"{title}"']
    if artist:
        query_parts.append(f'artist:"{artist}"')
    query = " AND ".join(query_parts)
    url = f"{MB_BASE}/recording/?query={urllib.parse.quote(query)}&fmt=json&limit=5"
    try:
        resp = _session().get(url, timeout=12)
        if resp.status_code != 200:
            return None
        recordings = resp.json().get("recordings") or []
        if not recordings:
            return None
        artist_l = (artist or "").lower()
        for rec in recordings:
            score = int(rec.get("score") or 0)
            if score < min_score:
                continue
            if artist_l:
                credit = rec.get("artist-credit") or []
                names = []
                for c in credit:
                    names.append(str(c.get("name") or "").lower())
                    names.append(str((c.get("artist") or {}).get("name") or "").lower())
                if names and not any(artist_l in n or n in artist_l for n in names if n):
                    continue
            return rec
        # High-score hit without artist filter only when artist was empty
        top = recordings[0]
        if int(top.get("score") or 0) >= min_score and not artist_l:
            return top
        return None
    except requests.RequestException:
        return None


def _cover_from_release(release_id: str, dest_path: str) -> bool:
    url = f"{CAA_BASE}/release/{release_id}/front-250"
    try:
        resp = _session().get(url, timeout=15, allow_redirects=True)
        if resp.status_code == 200 and resp.content and len(resp.content) > 100:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as fh:
                fh.write(resp.content)
            return True
    except requests.RequestException:
        return False
    return False


def _acoustid_lookup(path: str) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("ACOUSTID_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        # Prefer pyacoustid when installed; else call fpcalc + HTTP.
        try:
            import acoustid  # type: ignore

            results = list(acoustid.match(api_key, path))
            if not results:
                return None
            score, recording_id, title, artist = results[0]
            return {
                "score": score,
                "recording_id": recording_id,
                "title": title or "",
                "artist": artist or "",
            }
        except ImportError:
            pass

        fpcalc = os.getenv("FPCALC", "fpcalc")
        proc = subprocess.run(
            [fpcalc, "-json", path], capture_output=True, timeout=60, text=True
        )
        if proc.returncode != 0 or not proc.stdout:
            return None
        payload = json.loads(proc.stdout)
        duration = payload.get("duration")
        fingerprint = payload.get("fingerprint")
        if not fingerprint:
            return None
        params = {
            "client": api_key,
            "meta": "recordings artists releasegroups",
            "duration": int(float(duration or 0)),
            "fingerprint": fingerprint,
        }
        resp = _session().get(ACOUSTID_LOOKUP, params=params, timeout=15)
        if resp.status_code != 200:
            return None
        results = (resp.json() or {}).get("results") or []
        if not results:
            return None
        best = results[0]
        recordings = best.get("recordings") or []
        if not recordings:
            return None
        rec = recordings[0]
        artists = rec.get("artists") or []
        artist_name = artists[0].get("name", "") if artists else ""
        return {
            "score": best.get("score"),
            "recording_id": rec.get("id"),
            "title": rec.get("title") or "",
            "artist": artist_name,
        }
    except Exception:
        return None


def _tmdb_search(query: str) -> Optional[Dict[str, str]]:
    api_key = os.getenv("TMDB_API_KEY", "").strip()
    if not api_key or not query:
        return None
    try:
        resp = _session().get(
            TMDB_SEARCH,
            params={"api_key": api_key, "query": query},
            timeout=12,
        )
        if resp.status_code != 200:
            return None
        results = (resp.json() or {}).get("results") or []
        if not results:
            return None
        hit = results[0]
        title = hit.get("title") or hit.get("name") or ""
        date = (hit.get("release_date") or hit.get("first_air_date") or "")[:4]
        poster = hit.get("poster_path") or ""
        cover_url = f"https://image.tmdb.org/t/p/w342{poster}" if poster else ""
        return {"title": title, "year": date, "cover_url": cover_url, "overview": hit.get("overview") or ""}
    except requests.RequestException:
        return None


def enrich_metadata(path: str, cover_dest: Optional[str] = None) -> MediaMetadata:
    """Enrich metadata for a local media file using tags + free network APIs."""
    meta = MediaMetadata(path=path)
    if not path or not os.path.isfile(path):
        return meta

    tags = {}
    tags.update(_ffprobe_tags(path))
    tags.update({k: v for k, v in _mutagen_tags(path).items() if v})

    meta.title = tags.get("title") or tags.get("track") or ""
    meta.artist = tags.get("artist") or tags.get("album_artist") or tags.get("albumartist") or ""
    meta.album = tags.get("album") or ""
    meta.year = (tags.get("date") or tags.get("year") or "")[:4]
    meta.genre = tags.get("genre") or ""
    meta.source = "tags" if (meta.title or meta.artist) else "filename"

    fn_artist, fn_title = _parse_filename(path)
    if not meta.title:
        meta.title = fn_title
    if not meta.artist:
        meta.artist = fn_artist

    ext = os.path.splitext(path)[1].lower()
    is_audio = ext in {
        ".mp3",
        ".flac",
        ".wav",
        ".ogg",
        ".m4a",
        ".aac",
        ".wma",
        ".opus",
        ".ape",
    }
    is_video = ext in {
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".mpg",
        ".mpeg",
    }

    # AcoustID for audio when key present
    if is_audio:
        ac = _acoustid_lookup(path)
        if ac:
            if ac.get("title"):
                meta.title = ac["title"]
            if ac.get("artist"):
                meta.artist = ac["artist"]
            meta.source = "acoustid"
            meta.extra["acoustid"] = ac

    # MusicBrainz recording search (clean YouTube-style titles first)
    if is_audio and (meta.title or meta.artist):
        search_artist = _strip_release_noise(meta.artist)
        search_title = _strip_release_noise(meta.title)
        # Drop VEVO / Topic / channel suffixes from artist tags
        search_artist = re.sub(r"(?i)(vevo|topic|- topic)$", "", search_artist).strip()
        # "AdamDoleac" channel tags → "Adam Doleac"
        if search_artist and " " not in search_artist:
            spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", search_artist).strip()
            if spaced != search_artist:
                search_artist = spaced
        # Prefer "Artist - Title" inside the title field (common YouTube rips)
        if " - " in search_title:
            left, right = search_title.split(" - ", 1)
            left, right = left.strip(), right.strip()
            if left and right:
                # Use title-side artist when channel artist is empty/noisy
                if (not search_artist) or search_artist.lower() in {
                    left.lower(),
                    (left + "vevo").lower(),
                } or search_artist.lower().endswith("vevo"):
                    search_artist = left
                search_title = right
        rec = _musicbrainz_search(search_artist, search_title)
        # Title-only fallback only for distinctive titles (avoid "Famous"/"Alive" collisions)
        if not rec and search_title and len(search_title) >= 12 and not search_artist:
            time.sleep(1.05)
            rec = _musicbrainz_search("", search_title)
        if rec:
            meta.title = rec.get("title") or meta.title
            artist_credit = rec.get("artist-credit") or []
            if artist_credit:
                name = artist_credit[0].get("name") or artist_credit[0].get("artist", {}).get("name")
                if name:
                    meta.artist = name
            releases = rec.get("releases") or []
            if releases:
                meta.album = releases[0].get("title") or meta.album
                date = releases[0].get("date") or ""
                if date:
                    meta.year = date[:4]
                release_id = releases[0].get("id")
                if release_id and cover_dest:
                    if _cover_from_release(release_id, cover_dest):
                        meta.cover_path = cover_dest
            meta.source = "musicbrainz"
            meta.extra["mbid"] = rec.get("id")
            # Prefer CAA cover as library thumbnail when no embedded art
            if meta.cover_path and cover_dest:
                pass

    # TMDB for video when key present and tags look thin
    if is_video and os.getenv("TMDB_API_KEY", "").strip():
        query = meta.title or fn_title
        # Prefer cleaner heuristic title without extension junk
        tmdb = _tmdb_search(query)
        if tmdb and tmdb.get("title"):
            meta.title = tmdb["title"]
            if tmdb.get("year"):
                meta.year = tmdb["year"]
            meta.source = "tmdb"
            meta.extra["tmdb"] = tmdb
            cover_url = tmdb.get("cover_url") or ""
            if cover_url and cover_dest:
                try:
                    resp = _session().get(cover_url, timeout=15)
                    if resp.status_code == 200 and resp.content:
                        os.makedirs(os.path.dirname(cover_dest), exist_ok=True)
                        with open(cover_dest, "wb") as fh:
                            fh.write(resp.content)
                        meta.cover_path = cover_dest
                except requests.RequestException:
                    pass

    return meta
