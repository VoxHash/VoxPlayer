# Roadmap — VoxPlayer

Status as of October 2026 (v1.0.3). Goals are scoped to what the current PyQt6 + qBittorrent architecture can realistically deliver.

## Now (Q4 2026)

### Stability & packaging
- Keep CI green across Ubuntu, Windows, and macOS for Python 3.10–3.12
- Publish consistent release assets when build workflows produce them
- Harden qBittorrent auth/error messaging (banned IP, wrong credentials)

### Player fundamentals
- Playlist shuffle / repeat
- Clearer unsupported-format and missing-file messaging in the UI
- Keep volume amplification and resume positions reliable

### Documentation & contributor UX
- Keep the docs kit accurate against real install/run paths
- Expand automated tests beyond smoke imports when feasible in headless CI

## Next (H1 2027)

### Playback quality
- Broader codec coverage where Qt Multimedia / FFmpeg allows (HEVC, AV1, Opus as available)
- Subtitle format expansion (ASS/SSA/VTT) if maintainable without a second engine
- Optional light/dark theme polish and accessibility contrast pass

### Torrent streaming
- Safer defaults for sequential download and buffer thresholds
- Better multi-file torrent file picker UX
- Documented first-run Web UI setup wizard copy (no embedded secrets)

## Later (H2 2027+)

### Extensibility
- Small plugin hooks only if they stay optional and do not bloat the core player
- Media library / recent-files improvements

### Stretch (not committed)
- Mobile companion / remote control
- Cloud storage browsers
- Marketplace-style plugin distribution

Out of scope for the foreseeable roadmap: Web3, NFT, or “AI-powered” playback claims.

---

VoxHash Technologies · contact@voxhash.dev
