"""Minimal bencode decoder/encoder for .torrent metainfo (no third-party dep)."""

from __future__ import annotations

from typing import Any, Tuple


def decode(data: bytes) -> Any:
    value, offset = _decode_at(data, 0)
    if offset != len(data):
        # Some torrents append junk; accept if we parsed a top-level value.
        pass
    return value


def encode(value: Any) -> bytes:
    """Encode a Python object to bencode (for info-hash computation)."""
    if isinstance(value, int) and not isinstance(value, bool):
        return b"i" + str(value).encode("ascii") + b"e"
    if isinstance(value, bytes):
        return str(len(value)).encode("ascii") + b":" + value
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return str(len(raw)).encode("ascii") + b":" + raw
    if isinstance(value, list):
        return b"l" + b"".join(encode(v) for v in value) + b"e"
    if isinstance(value, dict):
        items = []
        for key in sorted(value.keys()):
            if isinstance(key, str):
                k = key.encode("utf-8")
            elif isinstance(key, bytes):
                k = key
            else:
                raise TypeError("bencode dict keys must be bytes or str")
            items.append(encode(k) + encode(value[key]))
        return b"d" + b"".join(items) + b"e"
    raise TypeError(f"Cannot bencode type {type(value)!r}")


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
