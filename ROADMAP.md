# Roadmap — VoxPlayer

Status as of October 2026 (**v1.49.0**). Stack: **PyQt6 shell** + **native-C-core-only playback** (python-vlc + system libvlc). No Qt Multimedia playback path.

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
3. **Playback**: prefer a maintained native media backend on Android (ExoPlayer-class or a native media core on Android) with the same volume/mute semantics as desktop (**Done 1.27.0** — Media3 ExoPlayer; Connect sheet for Wi‑Fi desktop discovery; volume 0–200 parity in **1.34.0**)
4. **Sync**: optional pull of playlists / podcast feeds from the desktop daemon; no cloud account required (**Done 1.28.0** — `GET /playlists` + `GET /podcasts`; companion Sync over Wi‑Fi or Bluetooth RFCOMM; on-device cache under app files)
5. **Bluetooth control**: dedicated RFCOMM profile for GrapheneOS (no Google Nearby) (**Done 1.28.0** — desktop `voxplayer.bt_control` SPP UUID + channel 5; Android Connect sheet pairs → RFCOMM)
6. **Background playback**: keep on-device audio playing when the UI is backgrounded (**Done 1.30.0** — Media3 `MediaSessionService` + `mediaPlayback` foreground service; system media notification; MediaController in the activity)
7. **Playback resumption**: restore last on-device item + position after process death via Media3 `MediaButtonReceiver` + `onPlaybackResumption` (**Done 1.31.0** — local prefs queue store; headset / media-key resume; intentional Stop clears the store)
8. **Gapless local queues + richer Now Playing**: play tapped library item as a Media3 playlist (same-kind continuity); prev/next track; artist/album/queue index in Now Playing (**Done 1.32.0** — `setMediaItems` gapless transitions where encoder delay/padding allows; MediaStore album tags)
9. **On-device repeat / shuffle + queue reorder**: Media3 `REPEAT_MODE_*` + shuffle; Up Next list with move up/down / remove (**Done 1.33.0** — prefs persist modes; transport + Now Playing controls)
10. **On-device volume 0–200 + mute**: desktop-parity logical volume; 0–100% via ExoPlayer volume, 101–200% via AOSP `LoudnessEnhancer` (~+6 dB at 200%); mute toggle (**Done 1.34.0**)
11. **On-device sound output + EQ**: `AudioManager` output device picker (speaker / wired / BT A2DP / USB / HDMI) via Media3 `setPreferredAudioDevice`; AOSP `Equalizer` presets (Off/Flat/Bass/Treble/Vocal/Loud) (**Done 1.35.0** — no GMS)
12. **Headset / Car media buttons + Quest route edge cases**: Media3 ±15s seek media-button preferences for Bluetooth AVRCP / System UI (no GMS Auto); `AudioDeviceCallback` re-applies preferred sink or falls back when it disconnects; activity resume re-binds audio chain (**Done 1.36.0**)
13. **Sleep timer + local bookmarks**: service-backed sleep timer (15–90 min, fade then pause); per-URI resume bookmarks stored on-device (autosave while playing, Now Playing list) (**Done 1.37.0** — no cloud)
14. **On-device play history facets**: scrobble-free Recently / Most-played from local JSON; Home filter chips; no Last.fm / cloud (**Done 1.38.0**)
15. **On-device playlist folders + smart lists**: manual playlist folders (add Now Playing); smart lists (New / Recent / Top / Short ≤3 min); no cloud (**Done 1.39.0**)
16. **Local lyrics / timed text**: sidecar `.lrc` / `.srt` / `.vtt` / `.txt` beside the media file; Now Playing panel with timed highlight; no cloud scrape (**Done 1.40.0**)
17. **Crossfade / gapless mixed-codec polish**: soft fade-in on auto transitions; optional skip-silence; same-kind queue filter for mixed A/V playlists (**Done 1.41.0**)
18. **Home-screen media widget**: classic AppWidget (no GMS Glance) — title + play/pause / prev / next via `PlaybackService` foreground intents (**Done 1.42.0**)
19. **Bluetooth AVRCP metadata richness**: Media3 session metadata with display title, subtitle, duration, album-art URI for headset / car / System UI (no GMS Auto) (**Done 1.43.0**)
20. **Landscape driving layout**: large-hit-target car mode when wide landscape (≥900dp); big transport + Recent; no GMS Auto (**Done 1.44.0**)
21. **Quest panel / foldable multi-window**: Jetpack WindowManager fold + multi-window awareness; compact panel chrome when height is short; configChanges keep playback alive; hinge padding (**Done 1.45.0**)
22. **Offline artwork thumbnails**: MediaStore `loadThumbnail` / album-art URIs in Home grid + Recent/Top cards; no cloud CDN (**Done 1.46.0**)
23. **Local library search**: title / artist / album substring filter on Home + Recent/Top (**Done 1.47.0**)
24. **DLNA / UPnP cast opt-in**: discover LAN MediaRenderers and cast Now Playing via FOSS UPnPCast (no Google Cast / GMS) (**Done 1.48.0**)
25. **Share now-playing card**: offline PNG card (title/artist/album/art) via system share sheet; FileProvider cache; no cloud (**Done 1.49.0**)


GrapheneOS constraints: Prefer FOSS dependencies, avoid proprietary push/analytics SDKs, document battery and background playback limits honestly.

**Background / battery (honest limits):** Local playback uses a standard Android `mediaPlayback` foreground service and a media-style notification (no proprietary keep-alive or analytics SDKs). Force-stop, denying notifications (on Android 13+), or aggressive battery restrictions can still end playback. Quest / Horizon OS may suspend or resize the 2D panel when unfocused; audio continues while the session service remains running. Gapless queues use the Media3 playlist API (encoder delay/padding honored when present). Resumption after process death relies on the last URI still being readable (scoped storage / SAF grants); force-stop may block automatic resume until the user opens the app again.

---

## Stretch (H2 2027+)

- Optional plugin hooks that stay out of the core path (**Done 1.21.0** — `~/.config/voxplayer/plugins/` + `voxplayer.plugins` entry points; Help → Plugins)
- WebAssembly / TUI clients talking to the local daemon (**Done 1.22.0** — `voxplayer-tui` / `voxplayer-ctl`; browser UI at daemon `/ui` with CORS for external / WASM hosts)
- Packaging: ship the native C media core (or clear per-OS installers) inside desktop bundles for Windows/macOS/Linux (**Done 1.23.0** — PyInstaller onedir + `native_core/`; `packaging/install_native_core_*`; CI installs core before bundle)
- Continue growing the native (Rust / C / optional Zig) surface area for scan, metadata, and other hot paths so the PyQt6 shell stays light under heavy multitasking (**Done 1.24.0** — Phase 6 `vox_scan_dir_meta` / `vox_scan_quick_ids`; Zig meta via `statx`; library index off Python `stat`)

---

VoxHash Technologies · contact@voxhash.dev
