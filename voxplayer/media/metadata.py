"""
Offline-first metadata enrichment.

Policy:
1. Local tags / ffprobe / filename heuristics always work with no network.
2. Remote lookups run only when connectivity is available.
3. Remote results are fetched at most once per file identity (path + size + mtime)
   and persisted under ~/.cache/voxplayer/metadata/.
4. Re-fetch only when the user explicitly refreshes.
5. Local embedded tags win for display; network data fills empty gaps unless
   an explicit refresh replaces them.

Optional keys (env / local .env only — never commit):
  ACOUSTID_API_KEY, TMDB_API_KEY, FPCALC
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple

import requests

USER_AGENT = "VoxPlayer/1.2.0 (https://github.com/VoxHash/VoxPlayer; contact@voxhash.dev)"
MB_BASE = "https://musicbrainz.org/ws/2"
CAA_BASE = "https://coverartarchive.org"
ACOUSTID_LOOKUP = "https://api.acoustid.org/v2/lookup"
TMDB_SEARCH = "https://api.themoviedb.org/3/search/multi"

_ONLINE_CACHE: Dict[str, Any] = {"checked_at": 0.0, "online": False}
_ONLINE_TTL_SEC = 30.0


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
    identity: str = ""
    network_attempted: bool = False
    from_cache: bool = False

    def display_title(self) -> str:
        return self.title or (os.path.basename(self.path) if self.path else "Unknown")

    def display_subtitle(self) -> str:
        parts = [p for p in (self.artist, self.album, self.year) if p]
        if parts:
            return " · ".join(parts)
        if self.path:
            return os.path.dirname(self.path)
        return ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaMetadata":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in (data or {}).items() if k in known}
        kwargs.setdefault("extra", {})
        return cls(**kwargs)


def _cache_root() -> str:
    root = os.path.join(os.path.expanduser("~"), ".cache", "voxplayer", "metadata")
    os.makedirs(root, exist_ok=True)
    return root


def file_identity(path: str) -> str:
    """Stable identity: path + size + mtime (nanoseconds when available)."""
    try:
        st = os.stat(path)
        mtime = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
        raw = f"{os.path.abspath(path)}|{st.st_size}|{mtime}".encode("utf-8", errors="replace")
    except OSError:
        raw = os.path.abspath(path).encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()


def _cache_path(identity: str) -> str:
    return os.path.join(_cache_root(), f"{identity}.json")


def load_cached_metadata(identity: str) -> Optional[MediaMetadata]:
    path = _cache_path(identity)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        meta = MediaMetadata.from_dict(data.get("meta") or data)
        meta.identity = identity
        meta.network_attempted = bool(data.get("network_attempted", meta.network_attempted))
        meta.from_cache = True
        return meta
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def save_cached_metadata(meta: MediaMetadata, network_attempted: bool = True) -> None:
    if not meta.identity:
        meta.identity = file_identity(meta.path) if meta.path else ""
    if not meta.identity:
        return
    payload = {
        "identity": meta.identity,
        "network_attempted": bool(network_attempted),
        "saved_at": time.time(),
        "meta": meta.to_dict(),
    }
    try:
        with open(_cache_path(meta.identity), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=0)
    except OSError:
        pass


def is_online(force: bool = False) -> bool:
    """Lightweight connectivity probe (cached ~30s). Never raises."""
    now = time.time()
    if not force and (now - float(_ONLINE_CACHE["checked_at"])) < _ONLINE_TTL_SEC:
        return bool(_ONLINE_CACHE["online"])
    online = False
    try:
        resp = requests.head(
            "https://musicbrainz.org/",
            timeout=2.5,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        online = resp.status_code < 500
    except requests.RequestException:
        try:
            resp = requests.get(
                "https://1.1.1.1/",
                timeout=2.0,
                headers={"User-Agent": USER_AGENT},
            )
            online = resp.status_code < 500
        except requests.RequestException:
            online = False
    _ONLINE_CACHE["checked_at"] = now
    _ONLINE_CACHE["online"] = online
    return online


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
    if " - " in cleaned:
        left, right = cleaned.split(" - ", 1)
        return left.strip(), right.strip()
    return "", cleaned


def load_local_metadata(path: str) -> MediaMetadata:
    """Tags + filename only. Never touches the network."""
    meta = MediaMetadata(path=path, source="local")
    if not path or not os.path.isfile(path):
        return meta
    meta.identity = file_identity(path)

    tags: Dict[str, str] = {}
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
    return meta


def _merge_prefer_local(local: MediaMetadata, remote: MediaMetadata, replace: bool) -> MediaMetadata:
    """Merge remote into local. Local wins unless replace (explicit refresh)."""
    out = MediaMetadata(
        path=local.path or remote.path,
        identity=local.identity or remote.identity,
        network_attempted=True,
        from_cache=remote.from_cache,
        extra=dict(local.extra or {}),
    )
    out.extra.update(remote.extra or {})

    def pick(local_val: str, remote_val: str) -> str:
        if replace and remote_val:
            return remote_val
        return local_val or remote_val or ""

    out.title = pick(local.title, remote.title)
    out.artist = pick(local.artist, remote.artist)
    out.album = pick(local.album, remote.album)
    out.year = pick(local.year, remote.year)
    out.genre = pick(local.genre, remote.genre)
    out.cover_path = pick(local.cover_path, remote.cover_path)

    if replace and remote.source and remote.source not in {"local", "tags", "filename"}:
        out.source = remote.source
    elif remote.source and remote.source not in {"local", "tags", "filename"} and (
        not local.title or not local.artist or remote.cover_path
    ):
        out.source = remote.source if (not local.artist or not local.album) else local.source
    else:
        out.source = local.source or remote.source or "local"
    return out


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
        return {
            "title": title,
            "year": date,
            "cover_url": cover_url,
            "overview": hit.get("overview") or "",
        }
    except requests.RequestException:
        return None


def _fetch_remote_metadata(
    local: MediaMetadata, cover_dest: Optional[str], replace: bool
) -> MediaMetadata:
    """Network enrichment. Caller must ensure online. Never raises to UI."""
    remote = MediaMetadata(path=local.path, identity=local.identity, source="network")
    path = local.path
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

    seed_title = local.title
    seed_artist = local.artist
    fn_artist, fn_title = _parse_filename(path)

    try:
        if is_audio:
            ac = _acoustid_lookup(path)
            if ac:
                if ac.get("title"):
                    remote.title = ac["title"]
                if ac.get("artist"):
                    remote.artist = ac["artist"]
                remote.source = "acoustid"
                remote.extra["acoustid"] = ac

        if is_audio and (seed_title or seed_artist or remote.title):
            search_artist = _strip_release_noise(remote.artist or seed_artist)
            search_title = _strip_release_noise(remote.title or seed_title)
            search_artist = re.sub(r"(?i)(vevo|topic|- topic)$", "", search_artist).strip()
            if search_artist and " " not in search_artist:
                spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", search_artist).strip()
                if spaced != search_artist:
                    search_artist = spaced
            if " - " in search_title:
                left, right = search_title.split(" - ", 1)
                left, right = left.strip(), right.strip()
                if left and right:
                    if (not search_artist) or search_artist.lower() in {
                        left.lower(),
                        (left + "vevo").lower(),
                    } or search_artist.lower().endswith("vevo"):
                        search_artist = left
                    search_title = right
            rec = _musicbrainz_search(search_artist, search_title)
            if not rec and search_title and len(search_title) >= 12 and not search_artist:
                time.sleep(1.05)
                rec = _musicbrainz_search("", search_title)
            if rec:
                remote.title = rec.get("title") or remote.title
                artist_credit = rec.get("artist-credit") or []
                if artist_credit:
                    name = artist_credit[0].get("name") or artist_credit[0].get(
                        "artist", {}
                    ).get("name")
                    if name:
                        remote.artist = name
                releases = rec.get("releases") or []
                if releases:
                    remote.album = releases[0].get("title") or remote.album
                    date = releases[0].get("date") or ""
                    if date:
                        remote.year = date[:4]
                    release_id = releases[0].get("id")
                    if release_id and cover_dest:
                        if _cover_from_release(release_id, cover_dest):
                            remote.cover_path = cover_dest
                remote.source = "musicbrainz"
                remote.extra["mbid"] = rec.get("id")

        if is_video and os.getenv("TMDB_API_KEY", "").strip():
            query = _strip_release_noise(seed_title or fn_title)
            tmdb = _tmdb_search(query)
            if tmdb and tmdb.get("title"):
                remote.title = tmdb["title"]
                if tmdb.get("year"):
                    remote.year = tmdb["year"]
                remote.source = "tmdb"
                remote.extra["tmdb"] = tmdb
                cover_url = tmdb.get("cover_url") or ""
                if cover_url and cover_dest:
                    try:
                        resp = _session().get(cover_url, timeout=15)
                        if resp.status_code == 200 and resp.content:
                            os.makedirs(os.path.dirname(cover_dest), exist_ok=True)
                            with open(cover_dest, "wb") as fh:
                                fh.write(resp.content)
                            remote.cover_path = cover_dest
                    except requests.RequestException:
                        pass
    except Exception:
        # Soft-fail: keep whatever remote fields we already have
        pass

    return _merge_prefer_local(local, remote, replace=replace)


def enrich_metadata(
    path: str,
    cover_dest: Optional[str] = None,
    force_refresh: bool = False,
    allow_network: bool = True,
) -> MediaMetadata:
    """
    Offline-first enrichment.

    - Always returns local tags immediately (no network required).
    - Uses disk cache when identity matches and network was already attempted.
    - Performs at most one remote fetch per identity unless force_refresh=True.
    - Skips remote work entirely when offline (no errors raised).
    """
    local = load_local_metadata(path)
    if not path or not os.path.isfile(path):
        return local

    cached = load_cached_metadata(local.identity)
    if cached and not force_refresh:
        merged = _merge_prefer_local(local, cached, replace=False)
        merged.network_attempted = bool(cached.network_attempted)
        merged.from_cache = True
        if cached.network_attempted or not allow_network:
            return merged
        # Cache exists but never attempted online (e.g. saved offline) — fall through

    if not allow_network:
        if cached:
            return _merge_prefer_local(local, cached, replace=False)
        return local

    if not is_online():
        # Persist local snapshot so we know we have not completed online yet
        local.network_attempted = False
        if cached:
            return _merge_prefer_local(local, cached, replace=False)
        save_cached_metadata(local, network_attempted=False)
        return local

    # Online: fetch once (or again on explicit refresh)
    if cached and cached.network_attempted and not force_refresh:
        return _merge_prefer_local(local, cached, replace=False)

    remote_merged = _fetch_remote_metadata(local, cover_dest, replace=force_refresh)
    remote_merged.network_attempted = True
    remote_merged.from_cache = False
    save_cached_metadata(remote_merged, network_attempted=True)
    return remote_merged
