# Roadmap — VoxPlayer

Status as of October 2026 (v1.1.0). Hybrid stack: **PyQt6 shell** + **Qt Multimedia** (always) with optional **libmpv** native decode when the window system allows embedding.

## Shipped in 1.1.0

- Modern four-pane desktop shell: left library rail, center home/stage, now-playing rail, bottom transport
- Unique VoxPlayer visual identity (ember accent on charcoal — not a clone of any streaming brand)
- Local file/folder library grid with search and type filters
- Playback path via Qt Multimedia; optional `voxplayer[native]` (python-mpv / libmpv) for hardware-oriented decode on X11
- Queue / playlist, seek, volume amplification, fullscreen, keyboard shortcuts retained
- qBittorrent Web UI torrent streaming retained

## Now (Q4 2026)

### Shell polish
- Persist home library roots across sessions
- Shuffle / repeat modes on the transport bar
- Stronger empty-state and unsupported-format messaging

### Playback
- Document and harden libmpv embed on Wayland (today defaults to Qt Multimedia under Wayland unless `VOXPLAYER_ENGINE=mpv`)
- Prefer zero-copy / hardware video surfaces where the platform compositor allows
- Clearer codec error surfacing when FFmpeg/Qt cannot open a stream

### Torrent streaming
- Safer sequential-download defaults and buffer thresholds
- Multi-file torrent picker UX
- First-run Web UI setup copy (no embedded secrets)

## Next (H1 2027)

### Native core migration (phased)
Industry media frameworks use C/C++ for demux → decode → output and Qt for the shell. VoxPlayer follows that direction without a big-bang rewrite:

1. Keep PyQt6 shell as the product surface
2. Expand libmpv (C) as the preferred decode/output path where embedding is stable
3. Evaluate a thin C++/Qt bridge only if Python bindings become a bottleneck
4. Retain qBittorrent integration at the Python layer (API client)

### Playback quality
- Broader codec coverage (HEVC, AV1, Opus) as backends allow
- Subtitle expansion (ASS/SSA/VTT) if maintainable without a second engine
- Accessibility contrast pass on the dark shell

## Later (H2 2027+)

- Optional plugin hooks that stay out of the core path
- Media library indexing / watch folders
- Stretch only: remote companion control (not committed)



---

VoxHash Technologies · contact@voxhash.dev
