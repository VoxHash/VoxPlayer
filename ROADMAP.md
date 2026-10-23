# Roadmap — VoxPlayer

Status as of October 2026 (v1.2.1). Hybrid stack: **PyQt6 shell** + **libmpv preferred** (when system libmpv is present) with **Qt Multimedia** fallback.

## Shipped in 1.2.1

- Favorites / playlist chips, Remove-from-Favorites context menus, playlist picker with existing lists
- Queue dock removed; Clear Up next fully stops and resets transport
- Audio/Video-scoped metadata facets (Type facet removed); Expand/Minimize only in ⋯ menu

## Shipped in 1.2.0

- Audio keeps the library visible; video stage only for video or explicit expand
- Responsive grid/list library, metadata facet browse, Favorites/local playlists
- Streaming-style Now Playing header and tray background playback
- libmpv default for 0–200% volume; qbittorrent-api in main deps
- Smarter video posters (reject black frames)

## Shipped in 1.1.x

- Modern desktop shell with ember-on-charcoal VoxPlayer identity
- Offline-first metadata cache and enrichment extras
- Volume amplification path and thumbnail pipeline foundations
- qBittorrent Web UI torrent streaming with media-library gating

## Now (Q4 2026)

### Shell polish
- Persist home library roots across sessions
- Shuffle / repeat modes on the transport bar
- Stronger empty-state and unsupported-format messaging

### Playback
- Harden libmpv embed on pure Wayland (today prefers X11/XWayland when `DISPLAY` exists)
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
