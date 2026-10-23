"""Minimal bencode decoder for .torrent metainfo (no third-party dep)."""

from __future__ import annotations

from typing import Any, Tuple


def decode(data: bytes) -> Any:
    value, offset = _decode_at(data, 0)
    if offset != len(data):
        # Some torrents append junk; accept if we parsed a top-level value.
        pass
    return value


def _decode_at(data: bytes, i: int) -> Tuple[Any, int]:
    if i >= len(data):
        raise ValueError("Unexpected end of bencode data")
    ch = data[i : i + 1]
    if ch == b"i":
        j = data.index(b"e", i)
        return int(data[i + 1 : j]), j + 1
    if ch == b"l":
        i += 1
        out = []
        while data[i : i + 1] != b"e":
            item, i = _decode_at(data, i)
            out.append(item)
        return out, i + 1
    if ch == b"d":
        i += 1
        out = {}
        while data[i : i + 1] != b"e":
            key, i = _decode_at(data, i)
            if not isinstance(key, bytes):
                raise ValueError("Dictionary key must be bytes")
            val, i = _decode_at(data, i)
            out[key] = val
        return out, i + 1
    if ch.isdigit():
        colon = data.index(b":", i)
        length = int(data[i:colon])
        start = colon + 1
        end = start + length
        return data[start:end], end
    raise ValueError(f"Invalid bencode at offset {i}")
