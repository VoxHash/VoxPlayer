# Roadmap — VoxPlayer

Status as of October 2026 (**v1.29.0**). Stack: **PyQt6 shell** + **native-C-core-only playback** (python-vlc + system libvlc). No Qt Multimedia playback path.

## Shipped in 1.3.0

- Zone-aware drag-and-drop: Home/library **indexes only**; Now Playing / Up next / transport **play immediately**
- Scrollbar contrast and grab size on library + Up next; understated All / Video / Audio / Recent filter tabs
- **Definitive native volume**: native-engine volume 0–200 and mute; clear install failure if lib missing; `run.py` venv + preflight
- First native hot-path: Rust `vox_scan` cdylib + Python ctypes loader for parallel folder scans
- Honest Wayland note: prefer X11/XWayland for video embed; audio volume still works on pure Wayland

## Shipped in 1.2.1

- Favorites / playlist chips, Remove-from-Favorites context menus, playlist picker with existing lists
- Queue dock removed; Clear Up next fully stops and resets transport
- Audio/Video-scoped metadata facets; Expand/Minimize only in ⋯ menu

## Shipped in 1.2.0

- Audio keeps the library visible; video stage only for video or explicit expand
- Responsive grid/list library, metadata facet browse, Favorites/local playlists
- Streaming-style Now Playing header and tray background playback
- native C media core preferred for 0–200% volume; qbittorrent-api in main deps

## Shipped in 1.1.x

- Modern desktop shell with ember-on-charcoal VoxPlayer identity
- Offline-first metadata cache and enrichment extras
- Volume amplification path and thumbnail pipeline foundations
- qBittorrent Web UI torrent streaming with media-library gating

---

## Product milestones (post native Phase 0–5)

Native migration table Phases 0–5 are complete (Phase 4 remains an ongoing shell-only stance). Active work continues under **Now** below.

## Now (Q4 2026 → H1 2027)

### Shell polish
- Persist home library roots across sessions (**Done 1.8.0**)
- Shuffle / repeat modes on the transport bar (**Done 1.8.0**)
- Skin / theme variety (bundled palettes + user theme packs under a VoxPlayer config dir) (**Done 1.9.0**)
- Stronger empty-state and unsupported-format messaging (**Done 1.9.0**)

### Playback (native-C-core-only)
- Soft WID rebind on show/resize; hard rebind only when the native window is recreated (**Done 1.7.0**)
- Coalesced non-blocking seeks with bounded retries (**Done 1.7.0**)
- Clearer codec error surfacing from the native engine (no silent engine switches) (**Done 1.10.0**)
- Further Wayland compositor embed when available without a second media stack (**Done 1.11.0**)

### Library & indexing
- Expand Rust `vox_scan` usage (watch folders, incremental re-scan) (**Done 1.12.0**)
- Metadata workers in native code (tags / covers off the UI thread) (**Done 1.5.0**)
- Deeper library facets (albums, artists, play counts, recently played / never played) (**Done 1.12.0**)

### Torrent streaming
- Safer sequential-download defaults and buffer thresholds (**Done 1.11.0**)
- Multi-file torrent picker UX (**Done 1.3.3**)
- First-run Web UI setup copy (no embedded secrets) (**Done 1.11.0**)

---

## Native performance migration (concrete phases)

Industry desktop players keep demux → decode → output in C/native code and reserve dynamic languages for the shell. VoxPlayer follows that path without a big-bang rewrite.

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **0** | native C media core as the **only** playback engine; volume/mute via engine properties | **Done (1.3.0)** |
| **1** | Rust `vox_scan` cdylib + ctypes for parallel folder walks | **Done (1.3.0)** — see `native/vox_scan` |
| **2** | Rust/C metadata + thumbnail worker pool (queue from Python, results via callbacks) | **Done (1.5.0)** — see `native/vox_meta` |
| **3** | Optional Zig experiments for alternate scanners / packagers if Rust artifacts are heavy | **Done (1.6.0)** — see `native/vox_scan_zig` |
| **4** | Keep PyQt6 as the product surface; avoid second playback engines | Ongoing |
| **5** | Harden in-app video WID embed + non-blocking seeks on all desktop targets | **Done (1.7.0)** |
| **6** | Grow scan/metadata hot paths: parallel ``vox_scan_dir_meta`` + blake3 ``vox_scan_quick_ids``; library index uses native stats | **Done (1.24.0)** |

**Long-run stance:** Keep investing in Rust/C (and Zig where it helps packaging) for hot paths so memory and parallel work stay efficient while the desktop shell remains PyQt6. That is how the project stays robust as library size and features grow.

Build Phase 1–2: `cargo build --release --manifest-path native/Cargo.toml` (`libvox_scan.so`, `libvox_meta.so`).

Build Phase 3 (optional lighter scanner): `native/vox_scan_zig/build.sh` → `native/target/zig-release/libvox_scan_zig.so` (Python prefers Zig over Rust when both exist).

---

## Next (H1–H2 2027)

### Daemon / remote control
- Optional local control daemon (HTTP/gRPC-style or MPD-compatible surface) so phones and scripts can drive playback on a trusted LAN (**Done 1.13.0** — localhost HTTP; LAN opt-in via `VOXPLAYER_DAEMON_ALLOW_LAN`)
- Desktop media-key / MPRIS integration where the OS expects it (**Done 1.13.0**)
- Multi-room / cast-style outputs only if maintainable without a second media stack (**Done 1.15.0** — LAN peer sync via control daemon; no Chromecast/AirPlay SDK)

### Podcast-like feeds & sync ideas
- Subscribe to RSS/Atom audio feeds; download episodes into the library (**Done 1.13.0**)
- Detect portable / USB media devices and sync playlists or podcast episodes with one action (**Done 1.14.0** — Media → Portable Devices)
- Hardware / open-firmware portable-player concepts: gapless queues, bookmark resume, simple on-device library views (desktop companion first) (**Done 1.16.0** — Audio → Playback companion; Media → Portable Devices → Browse On-Device Library)

### Library UX (streaming-style shells)
- Albums / Artists / Tracks / Liked navigation alongside the current Home grid (**Done 1.17.0**)
- Analytics-style views: most played, recently added, never played (local-only, privacy-first) (**Done 1.12.0** facets — Recently / Never / Most played)
- Waveform / spectrum meter as optional transport chrome (**Done 1.18.0** — View → Spectrum / waveform meter; real PCM via ffmpeg)

### Playback quality
- Broader codec coverage (HEVC, AV1, Opus) as the native C core allows (**Done 1.19.0** — extensions + avcodec/hw hints; Help → Codec support)
- Subtitle expansion (ASS/SSA/VTT) if maintainable on the single engine (**Done 1.13.0**)
- Accessibility contrast pass on the dark shell (**Done 1.20.0** — AA palette lift; View → Accessibility → High contrast)

---

## Later — Mobile (Android / GrapheneOS)

A **separate Android app phase** (not a thin WebView wrapper):

1. **Read-only companion**: browse library + remote-control a desktop/daemon instance on the LAN (**Done 1.25.0** — `android/` Compose+OkHttp companion; daemon `GET /library`; LAN or `adb reverse`)
2. **On-device library**: local files, offline cache, GrapheneOS-friendly permissions (storage scoped, no Google Play Services required) (**Done 1.27.0** — MediaStore + SAF; READ_MEDIA_* )
3. **Playback**: prefer a maintained native media backend on Android (ExoPlayer-class or a native media core on Android) with the same volume/mute semantics as desktop (**Done 1.27.0** — Media3 ExoPlayer; Connect sheet for Wi‑Fi desktop discovery)
4. **Sync**: optional pull of playlists / podcast feeds from the desktop daemon; no cloud account required (**Done 1.28.0** — `GET /playlists` + `GET /podcasts`; companion Sync over Wi‑Fi or Bluetooth RFCOMM; on-device cache under app files)
5. **Bluetooth control**: dedicated RFCOMM profile for GrapheneOS (no Google Nearby) (**Done 1.28.0** — desktop `voxplayer.bt_control` SPP UUID + channel 5; Android Connect sheet pairs → RFCOMM)

GrapheneOS constraints: Prefer FOSS dependencies, avoid proprietary push/analytics SDKs, document battery and background playback limits honestly.

---

## Stretch (H2 2027+)

- Optional plugin hooks that stay out of the core path (**Done 1.21.0** — `~/.config/voxplayer/plugins/` + `voxplayer.plugins` entry points; Help → Plugins)
- WebAssembly / TUI clients talking to the local daemon (**Done 1.22.0** — `voxplayer-tui` / `voxplayer-ctl`; browser UI at daemon `/ui` with CORS for external / WASM hosts)
- Packaging: ship the native C media core (or clear per-OS installers) inside desktop bundles for Windows/macOS/Linux (**Done 1.23.0** — PyInstaller onedir + `native_core/`; `packaging/install_native_core_*`; CI installs core before bundle)
- Continue growing the native (Rust / C / optional Zig) surface area for scan, metadata, and other hot paths so the PyQt6 shell stays light under heavy multitasking (**Done 1.24.0** — Phase 6 `vox_scan_dir_meta` / `vox_scan_quick_ids`; Zig meta via `statx`; library index off Python `stat`)

---

VoxHash Technologies · contact@voxhash.dev
