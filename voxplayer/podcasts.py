"""RSS/Atom podcast feed subscribe + episode download into the local library."""

from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen

_UA = "VoxPlayer/1.13 (+https://github.com/VoxHash/VoxPlayer; contact@voxhash.dev)"


def _config_path() -> str:
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = xdg if xdg else os.path.join(os.path.expanduser("~"), ".config")
    root = os.path.join(base, "voxplayer")
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "podcasts.json")


def podcasts_dir() -> str:
    xdg = os.environ.get("XDG_CACHE_HOME", "").strip()
    base = xdg if xdg else os.path.join(os.path.expanduser("~"), ".cache")
    path = os.path.join(base, "voxplayer", "podcasts")
    os.makedirs(path, exist_ok=True)
    return path


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


@dataclass
class Episode:
    title: str
    guid: str
    enclosure_url: str
    published: str = ""
    duration: str = ""
    local_path: str = ""


@dataclass
class PodcastFeed:
    url: str
    title: str = ""
    link: str = ""
    description: str = ""
    episodes: List[Episode] = field(default_factory=list)
    added_at: float = 0.0
    last_fetch: float = 0.0


class PodcastStore:
    def __init__(self):
        self.feeds: Dict[str, PodcastFeed] = {}
        self.load()

    def load(self) -> None:
        path = _config_path()
        if not os.path.isfile(path):
            self.feeds = {}
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError, TypeError):
            self.feeds = {}
            return
        feeds = {}
        for item in data.get("feeds") or []:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            eps = []
            for e in item.get("episodes") or []:
                if not isinstance(e, dict):
                    continue
                eps.append(
                    Episode(
                        title=str(e.get("title") or "Episode"),
                        guid=str(e.get("guid") or e.get("enclosure_url") or ""),
                        enclosure_url=str(e.get("enclosure_url") or ""),
                        published=str(e.get("published") or ""),
                        duration=str(e.get("duration") or ""),
                        local_path=str(e.get("local_path") or ""),
                    )
                )
            feed = PodcastFeed(
                url=str(item["url"]),
                title=str(item.get("title") or ""),
                link=str(item.get("link") or ""),
                description=str(item.get("description") or ""),
                episodes=eps,
                added_at=float(item.get("added_at") or 0),
                last_fetch=float(item.get("last_fetch") or 0),
            )
            feeds[feed.url] = feed
        self.feeds = feeds

    def save(self) -> None:
        payload = {
            "feeds": [
                {
                    **{k: v for k, v in asdict(f).items() if k != "episodes"},
                    "episodes": [asdict(e) for e in f.episodes[:200]],
                }
                for f in self.feeds.values()
            ]
        }
        path = _config_path()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, path)

    def subscribe(self, url: str) -> PodcastFeed:
        url = (url or "").strip()
        if not url:
            raise ValueError("Feed URL is empty")
        feed = fetch_feed(url)
        feed.added_at = time.time()
        existing = self.feeds.get(url)
        if existing:
            # Preserve downloaded local_path by guid
            by_guid = {e.guid: e for e in existing.episodes if e.guid}
            for ep in feed.episodes:
                old = by_guid.get(ep.guid)
                if old and old.local_path:
                    ep.local_path = old.local_path
            feed.added_at = existing.added_at or feed.added_at
        self.feeds[url] = feed
        self.save()
        return feed

    def unsubscribe(self, url: str) -> None:
        self.feeds.pop(url, None)
        self.save()

    def refresh(self, url: Optional[str] = None) -> List[PodcastFeed]:
        targets = [url] if url else list(self.feeds.keys())
        out = []
        for u in targets:
            if not u:
                continue
            try:
                out.append(self.subscribe(u))
            except Exception:
                continue
        return out


def _text(el: Optional[ET.Element]) -> str:
    if el is None or el.text is None:
        return ""
    return " ".join(el.text.split())


def fetch_feed(url: str, timeout: float = 25.0) -> PodcastFeed:
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    tag = _local(root.tag).lower()
    if tag == "feed":
        return _parse_atom(url, root)
    # RSS 2.0 / RDF
    channel = root.find("channel")
    if channel is None:
        # namespaced
        for child in root:
            if _local(child.tag).lower() == "channel":
                channel = child
                break
    if channel is None:
        raise ValueError("Not a recognized RSS/Atom feed")
    return _parse_rss(url, channel)


def _parse_rss(url: str, channel: ET.Element) -> PodcastFeed:
    title = ""
    link = ""
    desc = ""
    episodes: List[Episode] = []
    for child in channel:
        name = _local(child.tag).lower()
        if name == "title" and not title:
            title = _text(child)
        elif name == "link" and not link:
            link = _text(child) or (child.get("href") or "")
        elif name == "description" and not desc:
            desc = _text(child)
        elif name == "item":
            ep = _rss_item(child)
            if ep and ep.enclosure_url:
                episodes.append(ep)
    return PodcastFeed(
        url=url,
        title=title or url,
        link=link,
        description=desc,
        episodes=episodes,
        last_fetch=time.time(),
    )


def _rss_item(item: ET.Element) -> Optional[Episode]:
    title = ""
    guid = ""
    enclosure = ""
    published = ""
    duration = ""
    for child in item:
        name = _local(child.tag).lower()
        if name == "title":
            title = _text(child)
        elif name == "guid":
            guid = _text(child)
        elif name == "pubdate":
            published = _text(child)
        elif name == "duration":
            duration = _text(child)
        elif name == "enclosure":
            enclosure = child.get("url") or enclosure
        elif name == "link" and not enclosure:
            href = _text(child) or child.get("href") or ""
            if href.lower().endswith((".mp3", ".m4a", ".ogg", ".opus", ".aac", ".flac")):
                enclosure = href
    if not enclosure:
        return None
    return Episode(
        title=title or "Episode",
        guid=guid or enclosure,
        enclosure_url=enclosure,
        published=published,
        duration=duration,
    )


def _parse_atom(url: str, feed: ET.Element) -> PodcastFeed:
    title = ""
    link = ""
    desc = ""
    episodes: List[Episode] = []
    for child in feed:
        name = _local(child.tag).lower()
        if name == "title" and not title:
            title = _text(child)
        elif name == "subtitle" and not desc:
            desc = _text(child)
        elif name == "link":
            rel = (child.get("rel") or "alternate").lower()
            href = child.get("href") or ""
            if rel in {"alternate", ""} and href and not link:
                link = href
            elif rel == "enclosure" and href:
                pass
        elif name == "entry":
            ep = _atom_entry(child)
            if ep and ep.enclosure_url:
                episodes.append(ep)
    return PodcastFeed(
        url=url,
        title=title or url,
        link=link,
        description=desc,
        episodes=episodes,
        last_fetch=time.time(),
    )


def _atom_entry(entry: ET.Element) -> Optional[Episode]:
    title = ""
    guid = ""
    enclosure = ""
    published = ""
    for child in entry:
        name = _local(child.tag).lower()
        if name == "title":
            title = _text(child)
        elif name == "id":
            guid = _text(child)
        elif name in {"updated", "published"} and not published:
            published = _text(child)
        elif name == "link":
            rel = (child.get("rel") or "").lower()
            href = child.get("href") or ""
            typ = (child.get("type") or "").lower()
            if rel == "enclosure" or typ.startswith("audio/") or href.lower().endswith(
                (".mp3", ".m4a", ".ogg", ".opus", ".aac")
            ):
                enclosure = href or enclosure
    if not enclosure:
        return None
    return Episode(
        title=title or "Episode",
        guid=guid or enclosure,
        enclosure_url=enclosure,
        published=published,
    )


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\s.\-]+", "", name, flags=re.UNICODE).strip()
    name = re.sub(r"\s+", "_", name)
    return (name or "episode")[:120]


def download_episode(episode: Episode, feed_title: str = "") -> str:
    """Download enclosure into the podcasts cache; return local path."""
    if not episode.enclosure_url:
        raise ValueError("Episode has no enclosure URL")
    if episode.local_path and os.path.isfile(episode.local_path):
        return episode.local_path
    parsed = urlparse(episode.enclosure_url)
    ext = os.path.splitext(parsed.path)[1].lower() or ".mp3"
    if ext not in {".mp3", ".m4a", ".ogg", ".opus", ".aac", ".flac", ".wav", ".mp4"}:
        ext = ".mp3"
    folder = os.path.join(podcasts_dir(), _safe_filename(feed_title or "feed"))
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, _safe_filename(episode.title) + ext)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        episode.local_path = dest
        return dest
    req = Request(episode.enclosure_url, headers={"User-Agent": _UA})
    with urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)
    episode.local_path = dest
    return dest
