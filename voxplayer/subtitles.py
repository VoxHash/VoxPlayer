"""Subtitle loaders for SRT, WebVTT, and basic ASS/SSA Dialogue lines."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

Cue = Dict[str, object]  # start:int ms, end:int ms, text:str

_SUB_EXTS = (".srt", ".vtt", ".ass", ".ssa")


def companion_subtitle_paths(media_path: str) -> List[str]:
    """Return existing sidecar subtitle files next to a media path."""
    if not media_path:
        return []
    stem = os.path.splitext(media_path)[0]
    out = []
    for ext in _SUB_EXTS:
        cand = stem + ext
        if os.path.isfile(cand):
            out.append(cand)
    # Also language-tagged: video.en.srt
    parent = os.path.dirname(media_path)
    base = os.path.basename(stem)
    try:
        for name in os.listdir(parent or "."):
            lower = name.lower()
            if not any(lower.endswith(ext) for ext in _SUB_EXTS):
                continue
            if lower.startswith(base.lower() + ".") or lower.startswith(base.lower() + "_"):
                full = os.path.join(parent, name)
                if full not in out:
                    out.append(full)
    except OSError:
        pass
    return out


def load_subtitle_file(path: str) -> List[Cue]:
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    if ext == ".vtt":
        return parse_vtt(content)
    if ext in {".ass", ".ssa"}:
        return parse_ass(content)
    return parse_srt(content)


def parse_srt(content: str) -> List[Cue]:
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks = content.strip().split("\n\n")
    cues: List[Cue] = []
    for block in blocks:
        lines = [ln for ln in block.strip().split("\n") if ln.strip() != ""]
        if len(lines) < 2:
            continue
        # Optional index line
        if "-->" not in lines[0] and len(lines) >= 3:
            time_line, text_lines = lines[1], lines[2:]
        elif "-->" in lines[0]:
            time_line, text_lines = lines[0], lines[1:]
        else:
            continue
        try:
            start, end = _parse_arrow_times(time_line, srt=True)
        except Exception:
            continue
        text = _strip_tags("\n".join(text_lines))
        if text:
            cues.append({"start": start, "end": end, "text": text})
    return cues


def parse_vtt(content: str) -> List[Cue]:
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    # Drop header / NOTE / STYLE blocks roughly
    body = content
    if body.lstrip().upper().startswith("WEBVTT"):
        # skip until first blank after header
        parts = body.split("\n\n", 1)
        body = parts[1] if len(parts) > 1 else ""
    cues: List[Cue] = []
    for block in body.split("\n\n"):
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        if not lines:
            continue
        if lines[0].upper().startswith(("NOTE", "STYLE", "REGION")):
            continue
        if "-->" not in lines[0] and len(lines) >= 2 and "-->" in lines[1]:
            time_line, text_lines = lines[1], lines[2:]
        elif "-->" in lines[0]:
            time_line, text_lines = lines[0], lines[1:]
        else:
            continue
        try:
            start, end = _parse_arrow_times(time_line, srt=False)
        except Exception:
            continue
        text = _strip_tags("\n".join(text_lines))
        if text:
            cues.append({"start": start, "end": end, "text": text})
    return cues


_ASS_DIALOGUE = re.compile(
    r"^Dialogue:\s*(?:Marked=\d+,)?(?P<layer>\d+),(?P<start>[^,]+),(?P<end>[^,]+),"
    r"(?P<style>[^,]*),(?P<name>[^,]*),(?P<mL>\d+),(?P<mR>\d+),(?P<mV>\d+),"
    r"(?P<effect>[^,]*),(?P<text>.*)$",
    re.IGNORECASE,
)


def parse_ass(content: str) -> List[Cue]:
    """Extract plain text from ASS/SSA Dialogue lines (overlay fallback)."""
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    cues: List[Cue] = []
    for line in content.split("\n"):
        line = line.strip()
        if not line.lower().startswith("dialogue:"):
            continue
        m = _ASS_DIALOGUE.match(line)
        if not m:
            # Fallback split: Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,text
            parts = line.split(",", 9)
            if len(parts) < 10:
                continue
            start_s, end_s, text = parts[1], parts[2], parts[9]
        else:
            start_s, end_s, text = m.group("start"), m.group("end"), m.group("text")
        try:
            start = _ass_time_to_ms(start_s)
            end = _ass_time_to_ms(end_s)
        except Exception:
            continue
        text = _strip_ass_overrides(text)
        if text:
            cues.append({"start": start, "end": end, "text": text})
    return cues


def _parse_arrow_times(time_line: str, srt: bool) -> Tuple[int, int]:
    # Allow settings after arrow in VTT: 00:00:01.000 --> 00:00:04.000 align:start
    left, right = time_line.split("-->", 1)
    start = _clock_to_ms(left.strip(), srt=srt)
    end_token = right.strip().split()[0]
    end = _clock_to_ms(end_token, srt=srt)
    return start, end


def _clock_to_ms(token: str, srt: bool) -> int:
    token = token.strip().replace(",", ".")
    parts = token.split(":")
    if len(parts) == 3:
        h, m, rest = parts
        if "." in rest:
            s, frac = rest.split(".", 1)
            ms = int((frac + "000")[:3])
        else:
            s, ms = rest, 0
        return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + ms
    if len(parts) == 2:
        m, rest = parts
        if "." in rest:
            s, frac = rest.split(".", 1)
            ms = int((frac + "000")[:3])
        else:
            s, ms = rest, 0
        return (int(m) * 60 + int(s)) * 1000 + ms
    raise ValueError(token)


def _ass_time_to_ms(token: str) -> int:
    # H:MM:SS.cs (centiseconds)
    token = token.strip()
    h, m, rest = token.split(":", 2)
    if "." in rest:
        s, cs = rest.split(".", 1)
        ms = int((cs + "00")[:2]) * 10
    else:
        s, ms = rest, 0
    return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + ms


def _strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("&nbsp;", " ").strip()


def _strip_ass_overrides(text: str) -> str:
    text = text.replace("\\N", "\n").replace("\\n", "\n").replace("\\h", " ")
    text = re.sub(r"\{[^}]*\}", "", text)
    return text.strip()
