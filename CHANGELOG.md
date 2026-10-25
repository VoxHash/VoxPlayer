# Changelog — VoxPlayer

All notable changes to VoxPlayer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Further Android companion polish (gapless crossfade duration control)

## [1.52.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: **M3U export / import** — export Up Next or a playlist folder as offline `.m3u` (share sheet); import via SAF into a new on-device folder (URI / filename match; no cloud)

## [1.51.0] - 2026-10-24

### Changed
- Android / GrapheneOS / Quest: **EQ + sound output polish** — clear selected EQ presets with descriptions; sinks grouped by route (This device / Wired / Bluetooth / USB / Display) with explicit “Routing:” status

## [1.50.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: **Listening stats** — scrobble-free on-device listen events; Home **Week** / **Month** facets (listens, unique tracks, top artist); no Last.fm / cloud

## [1.49.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: **Share card** on Now Playing — offline PNG (title / artist / album / artwork) via system share sheet; FileProvider cache; no cloud upload

## [1.48.0] - 2026-10-24

### Added
- Android / GrapheneOS: opt-in **DLNA / UPnP cast** (FOSS UPnPCast via JitPack) — scan LAN MediaRenderers, cast Now Playing, play/pause/stop; no Google Cast SDK / GMS

## [1.47.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: local library search — filter Home / Recent / Top by title, artist, or album (on-device only)

## [1.46.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: offline library artwork — MediaStore thumbnails / album-art URIs on Home grid and history cards (no cloud)

## [1.45.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: Quest panel + foldable multi-window polish — Jetpack WindowManager fold/multi-window flags; compact panel chrome when window height is short; expanded `configChanges` so resize/fold does not recreate the activity; hinge side padding; audio chain rebind on config / multi-window changes

## [1.44.1] - 2026-10-24

### Fixed
- Android: duplicate `@Composable` on driving layout that broke the 1.44.0 debug APK build

## [1.44.0] - 2026-10-24

### Added
- Android / GrapheneOS: landscape driving layout (≥900dp wide landscape) — oversized Play/Pause/Prev/Next and Recent list; no Google Automotive

## [1.43.0] - 2026-10-24

### Added
- Android / GrapheneOS: richer Media3 session metadata for Bluetooth AVRCP / System UI — display title, artist·album subtitle, duration, MediaStore album-art URI (no GMS Auto)

## [1.42.0] - 2026-10-24

### Added
- Android / GrapheneOS: home-screen media widget (classic AppWidget, no GMS Glance) — title + play/pause / previous / next driven by `PlaybackService`

## [1.41.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: soft fade-in (~450ms) on auto track transitions; optional ExoPlayer skip-silence; same-kind continuity when a playlist mixes audio and video

## [1.40.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: local lyrics from sidecar `.lrc` / `.srt` / `.vtt` / `.txt` next to the media (MediaStore sibling or file path); Now Playing timed highlight; no cloud scrape

## [1.39.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: Home **Lists** — manual playlist folders (New list + Add Now Playing) and smart lists (New on device, Recently / Most played, Short audio ≤3 min); local JSON only, no cloud

## [1.38.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: scrobble-free play history — local JSON counts + last-played; Home **Recent** / **Top** facets; Clear history; no Last.fm / cloud

## [1.37.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: sleep timer (15/30/45/60/90 min) in `PlaybackService` — fades over the last ~30s then pauses; survives UI backgrounding
- Local per-URI resume bookmarks (autosave while playing + Save here); Now Playing list to resume or remove; no cloud

## [1.36.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: headset & System UI media-button polish — Media3 ±15s seek preferences (`COMMAND_SEEK_BACK` / `FORWARD`) for Bluetooth AVRCP; no Google Automotive / Auto SDK
- Quest / route edge cases: `AudioDeviceCallback` re-applies preferred sink or falls back to system default when it disconnects; activity resume re-binds volume/EQ/route

## [1.35.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: Sound Output device picker via `AudioManager` (no GMS) — system default or preferred sink routed with Media3 `setPreferredAudioDevice`
- AOSP `Equalizer` presets (Off / Flat / Bass / Treble / Vocal / Loud) attached to the Media3 audio session; Now Playing controls; prefs persist

## [1.34.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: local volume **0–200%** + mute matching desktop semantics — ExoPlayer volume for 0–100%, AOSP `LoudnessEnhancer` for boost above 100% (~+6 dB at 200%); prefs persist; transport + Now Playing controls

## [1.33.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: local repeat (off / all / one) and shuffle modes via Media3; modes persist in prefs
- Up Next queue panel: tap to play, move up/down, remove; transport shuffle/repeat icons on wide layouts

## [1.32.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: gapless local library queues via Media3 `setMediaItems` (play from tapped item; same-kind continuity under All filter; transport prev/next skips tracks)
- Richer Now Playing: MediaStore artist + album on cards and side panel; queue index (`n / N`) in transport and Now Playing
- Playback queue store persists the full playlist for process-death resumption

## [1.31.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: playback resumption after process death — persist last URI/title/position; Media3 `MediaButtonReceiver` + `onPlaybackResumption` restores the queue for headset / media-key play
- Intentional Stop clears the resumable store so empty resume requests fail cleanly (avoids empty-playlist FGS timeouts)

## [1.30.0] - 2026-10-24

### Added
- Android / GrapheneOS / Quest: Media3 `PlaybackService` (`MediaSessionService`) so on-device audio continues in the background with a system media notification
- Activity uses `MediaController` against the session service (lock screen / headset controls)
- ROADMAP Later item 6 (background playback) + honest battery / GrapheneOS limits note

## [1.29.1] - 2026-10-23

### Fixed
- System mixer branding: LibVLC Pulse stream now reports **VoxPlayer** name + `voxplayer` icon (not “VLC media player”) via `set_user_agent` / `set_app_id`; refresh XDG hicolor icon on startup
- Audio → Sound Output → Select Device enumerates all Pulse/PipeWire sinks from the native engine and applies the chosen device

## [1.29.0] - 2026-10-23

### Added
- Quest / Horizon OS panel sizing: default **1024×640 dp** (Meta common 2D app frame), min 360×225; `com.oculus.supportedDevices` for Quest 2/3/Pro/3S
- Companion shell aligned with desktop ember-on-charcoal: left rail, Home media grid, Now Playing side panel on wide layouts, full transport with Connect

### Changed
- Android / GrapheneOS / Quest UI: larger touch targets (≥44dp), readable type, no streaming-green accents — warm ember primary matching desktop

## [1.28.1] - 2026-10-23

### Added
- Desktop transport **Connect** button (far bottom-right) with companion Wi‑Fi / Bluetooth RFCOMM status dialog
- Android transport labeled **Connect** button (bottom-right) so the control is visible on phone and Quest

### Fixed
- Bluetooth RFCOMM server bind on BlueZ (`bad bluetooth address` when binding `""`) — bind the real adapter BDADDR
- Android RFCOMM client prefers channel 5 before SPP UUID SDP lookup (hosts without `sdptool`)

## [1.28.0] - 2026-10-23

### Added
- Dedicated Bluetooth RFCOMM control profile (`voxplayer/bt_control.py`, SPP UUID `00001101-…-05f9b34fb`, channel 5 / `VOXPLAYER_BT_CHANNEL`); same JSON-line commands as the HTTP daemon; `VOXPLAYER_BT=0` to disable
- Android Connect sheet: tap a paired Bluetooth device for RFCOMM remote control (GrapheneOS-friendly; no Google Nearby)
- Control daemon `GET /playlists` and `GET /podcasts` for companion sync (no cloud account)
- Android Sync: pull playlists + podcast feeds over Wi‑Fi or Bluetooth; cache under app files; play podcast enclosures on-device

### Changed
- ROADMAP Later item 4 (Sync) and Bluetooth control marked done for 1.28.0

## [1.27.0] - 2026-10-23

### Added
- Android / Quest app is a full on-device player: Media3 ExoPlayer for local audio/video, MediaStore library, SAF open, view intents
- Connect sheet (devices icon): pick **This device** or a desktop found on Wi‑Fi; tips for same network / VPN bypass / Bluetooth paired hints
- Desktop UDP discovery beacon (`voxplayer/discovery.py`, port 17891) so phones find the PC without USB
- GrapheneOS-friendly permissions (READ_MEDIA_* / Storage Scopes / SAF; no Google Nearby)

### Changed
- ROADMAP Later items 2–3 marked done for 1.27.0

## [1.26.0] - 2026-10-23

### Added
- `voxplayer-lan-bypass`: keep RFC1918 / home Wi‑Fi subnets on the physical LAN NIC so ProtonVPN (and similar) policy routing does not black-hole Android/Quest companions
- `voxplayer-usb-bridge`: collapse duplicate `adb` fork-servers and refresh `adb reverse` for USB companion e2e

### Fixed
- Companion USB workflow when dozens of IDE `adb` servers hide Pixel / Quest devices

## [1.25.0] - 2026-10-23

### Added
- Android / GrapheneOS-friendly LAN companion (`android/`): OkHttp + Compose; no GMS; browse desktop library + transport remote
- Control daemon `GET /library` (read-only indexed paths for companions)
- Companion intent extras `host` / `port` / `autoconnect` for USB `adb reverse` e2e

### Fixed
- Queue / track-advance false “Playback error” alerts: keep Opus in the native codec list (`dav1d,opus,avcodec,all`); suppress EncounteredError during load transitions and near EOS

### Changed
- ROADMAP Later item 1 (read-only companion) marked done for 1.25.0

## [1.24.1] - 2026-10-23

### Fixed
- Black video stage while audio plays: do not set `WA_DontCreateNativeAncestors` on X11/XWayland (VLC-upstream guidance); re-bind WID after map
- Prefer `--codec=dav1d,avcodec,all` so AV1 uses dav1d instead of an avcodec-first path that blanked frames
- Skip `--no-xlib` when embedding on X11/XWayland so the xcb vout can paint into the Qt surface
- About / update checker / daemon `version` read `voxplayer.__version__` (was hardcoded `1.13.0`)
- `setup.py` version derived from `voxplayer/__init__.py`

## [1.24.0] - 2026-10-23

### Added
- Phase 6 native scan ABI: `vox_scan_dir_meta` (parallel walk+stat TSV) and Rust `vox_scan_quick_ids` (blake3 of size/mtime/first 64KiB)
- Zig scanner gains `vox_scan_dir_meta` (linux `statx`) + shared `vox_scan_version`
- `library_index.scan_root` uses native meta when available (no per-file Python `stat` on the hot path)
- Loader prefers meta-capable builds, then quick-ids (Rust), then Zig

### Changed
- ROADMAP Stretch native-surface-area item and Phase 6 marked done

## [1.23.0] - 2026-10-23

### Added
- `voxplayer/native_core_paths.py` — discover system/bundled native C media core; activate in frozen apps
- PyInstaller **onedir** `voxplayer.spec` copies libvlc + plugins into `native_core/` when present on the build host
- Runtime hook `packaging/rthook_native_core.py`; Instance `--plugin-path` for bundled plugins
- Clear per-OS installers: `packaging/install_native_core_{linux,macos}.sh`, `install_native_core_windows.ps1`
- `packaging/build_desktop.sh`; CI installs the media core before Windows/macOS/Linux bundles

### Changed
- Debian packaging wraps the onedir bundle and depends on `vlc | libvlc5`
- ROADMAP Stretch packaging item marked done

## [1.22.0] - 2026-10-23

### Added
- Shared HTTP client for the control daemon (`voxplayer/daemon_client.py`)
- TUI + one-shot CLI remotes: `voxplayer-tui` / `voxplayer-ctl` (curses transport; Space/n/p/s/±/seek/open)
- Packaged browser remote under `voxplayer/web_client/`; served same-origin at daemon `GET /ui`
- CORS + `OPTIONS` on the control daemon so external pages and future WASM hosts can call the JSON API

### Changed
- ROADMAP Stretch WASM/TUI daemon-clients item marked done

## [1.21.0] - 2026-10-23

### Added
- Optional shell plugin hooks outside the native C core (`voxplayer/plugins.py`)
- Discover `~/.config/voxplayer/plugins/*.py` and pip entry points `voxplayer.plugins`
- Hooks: `on_app_ready`, `on_track_changed`, `on_playback_state`, `on_library_changed`, `contribute_actions`
- Help → Plugins… status; Help → Plugin actions menu; sample `example_nowplaying_log.py` written on first load
- Guard: plugins declaring `PROVIDES_PLAYBACK_ENGINE` are rejected; `VOXPLAYER_PLUGINS=0` disables all

### Changed
- ROADMAP Stretch plugin-hooks item marked done

## [1.20.0] - 2026-10-23

### Added
- Accessibility contrast pass: bundled dark palettes lift muted text (≥4.5:1) and borders (≥3:1) vs `bg_app` (WCAG 2.2 AA)
- View → Accessibility → High contrast overlay + Contrast report… (measured ratios)
- Stronger keyboard focus rings (2–3px `focus` outline) on buttons, fields, and lists

### Changed
- Status bar and library nav use secondary text for clearer chrome
- ROADMAP accessibility contrast item marked done; Next playback-quality block complete

## [1.19.0] - 2026-10-23

### Added
- HEVC (`.hevc`/`.h265`), AV1 (`.av1`/`.ivf`), and related containers in open/scan/index lists; Opus already covered, demux hints for elementary streams
- Native engine prefers `--codec=avcodec,all` and optional `--avcodec-hw` (`VOXPLAYER_AVCODEC_HW`, default `any`)
- Help → Codec support… probes local ffmpeg for HEVC/AV1/Opus decoders and HW accels
- Media Info shows ffprobe stream codec names

### Changed
- Central `voxplayer/codecs.py` owns format lists and capability probe
- ROADMAP broader codec coverage marked done

## [1.18.0] - 2026-10-23

### Added
- Optional transport spectrum meter + seekable waveform strip (View → Spectrum / waveform meter)
- Real PCM analysis via ffmpeg (same toolchain as thumbnails); playhead-synced band levels — libvlc audio output unchanged

### Changed
- ROADMAP waveform / spectrum chrome marked done

## [1.17.0] - 2026-10-23

### Added
- Streaming-style library nav: Albums / Artists / Tracks / Liked alongside the Home grid (Library rail opens Tracks by default)
- Liked maps to Favorites; Albums/Artists drill into tagged buckets; Tracks is a sorted flat audio list with search

### Changed
- ROADMAP Library UX Albums/Artists/Tracks/Liked marked done; analytics facets credited to 1.12.0

## [1.16.0] - 2026-10-23

### Added
- Gapless queue (best-effort): prefetch next audio on a second MediaPlayer from the same libvlc Instance; promote on natural end (Audio → Playback companion)
- Bookmark resume: persist per-file positions and seek on reopen; clear near end / Clear all bookmarks
- On-device library browse for USB `VoxPlayer/` folders (media + M3U) via Media → Portable Devices → Browse On-Device Library…

### Changed
- Natural track end emits `ended` (auto-advance / gapless); user Stop no longer auto-advances the queue
- ROADMAP portable-player companion item marked done

## [1.15.0] - 2026-10-23

### Added
- LAN multi-room transport sync: Audio → Multi-room fans out play/pause/stop/open/seek/volume to peer VoxPlayer control daemons (same native stack; peers need `VOXPLAYER_DAEMON_ALLOW_LAN=1`)
- Manage rooms (add/remove/test/toggle), Sync now, and setup help; config in `~/.config/voxplayer/multiroom.json`
- Inbound daemon commands do not re-broadcast (no leader↔follower echo loops)

### Changed
- ROADMAP multi-room item marked done (no second media / cast SDK)

## [1.14.0] - 2026-10-23

### Added
- Portable / USB device detection (`/proc/mounts` + removable sysfs; `/run/media/$USER` / `/media/$USER`) via Media → Portable Devices → List Detected Devices
- One-action sync of Favorites, named playlists, Up next, or downloaded podcast episodes onto a mounted volume under `VoxPlayer/` with an M3U playlist

### Changed
- ROADMAP portable / USB sync item marked done

## [1.13.0] - 2026-10-23

### Added
- MPRIS2 desktop integration (Linux session bus) for media keys / shell widgets (`VOXPLAYER_DISABLE_MPRIS=1` to opt out)
- Localhost HTTP control daemon on `127.0.0.1:17890` (`/status`, `/play`, `/pause`, `/next`, `/volume`, `/seek`, `/open`); LAN bind requires `VOXPLAYER_DAEMON_ALLOW_LAN=1`
- Podcasts: subscribe to RSS/Atom feeds, refresh, download episodes into `~/.cache/voxplayer/podcasts/` (Media → Podcasts)
- Subtitle expansion: WebVTT + ASS/SSA sidecars (native libvlc file bind preferred for ASS; overlay for SRT/VTT)

### Changed
- ROADMAP Next items for daemon/MPRIS, podcast subscribe/download, and subtitle expansion marked done

## [1.12.0] - 2026-10-23

### Added
- Watch-folder library roots via `QFileSystemWatcher` + debounced incremental re-scan (native `vox_scan` / Zig when built); fingerprints in `~/.cache/voxplayer/library_index.json`
- Periodic 60s catch-up poll for nested directory changes
- Deeper browse facets: Album; Recently / Never / Most played (local play counts + last played)
- Play stats recorded on play; facets refresh accordingly

### Changed
- ROADMAP library watch/incremental and deeper facets marked done

## [1.11.0] - 2026-10-23

### Added
- Wayland embed path: force X11/XWayland when `DISPLAY` is set; probe future `libvlc_media_player_set_wayland_surface`; skip XID bind on pure Wayland without that API; clearer embed status copy (`VOXPLAYER_EMBED` / `VOXPLAYER_FORCE_WAYLAND`)
- Safer torrent startup buffers (smaller audio/video bases, soft caps, env overrides `VOXPLAYER_TORRENT_BUFFER_MB` / `_PCT`); re-assert sequential + first/last piece priority
- First-run qBittorrent Web UI setup guide (Media → Torrent → Web UI Setup Guide) with no embedded secrets; connection errors reuse the same copy

### Changed
- ROADMAP Wayland embed, torrent buffer, and first-run Web UI items marked done

## [1.10.0] - 2026-10-23

### Added
- Native engine hooks `MediaPlayerEncounteredError` and Error-state polling with clear, once-per-source messages (file name, extension, libvlc errmsg)
- Playback error dialogs state explicitly that VoxPlayer never switches to another media stack

### Changed
- Ended vs Error states are distinguished in the engine poll loop (Error is no longer a quiet stop)
- ROADMAP codec-error surfacing marked done

## [1.9.0] - 2026-10-23

### Added
- Bundled theme palettes (Ember, Midnight, Slate, Graphite) via View → Theme
- User theme packs as JSON under `~/.config/voxplayer/themes/` (example Ocean pack written on first list)
- Stronger empty-library panel with next actions and supported-format hints
- Clear unsupported-format dialogs for Open / drop / empty folder, plus codec-oriented engine errors

### Changed
- Legacy `theme=dark|light` settings migrate to Ember
- ROADMAP shell-polish theme + empty/unsupported items marked done

### Fixed
- Theme work no longer breaks window launch (`COLORS` import required by shell chrome)

## [1.8.0] - 2026-10-23

### Added
- Persist Open Folder library roots across sessions (re-indexed on launch)
- Transport shuffle + repeat (off / all / one), with wrap and shuffled Up next order

### Changed
- ROADMAP shell-polish items for roots and shuffle/repeat marked done

## [1.7.0] - 2026-10-23

### Added
- Native Phase 5: hardened in-app video WID embed (soft rebind on show/resize; hard only when the Qt native window is recreated)
- Coalesced non-blocking seeks with bounded Opening/Buffering retries; scrub uses fractional position, release uses exact time

### Changed
- ROADMAP Phase 5 marked done; Phase 4 (PyQt6 shell-only) remains ongoing

## [1.6.0] - 2026-10-23

### Added
- Native Phase 3: Zig alternate folder scanner (`native/vox_scan_zig`) with the same C ABI as Rust `vox_scan`
- Python loader prefers the Zig shared library when present (~2.7× smaller than the Rust scanner on Linux)

### Changed
- ROADMAP Phase 3 marked done; Phase 5 (WID embed harden) is next

## [1.5.0] - 2026-10-23

### Added
- Native Phase 2: Rust `vox_meta` worker pool for off-UI-thread tags (ffprobe) and thumbnails (ffmpeg), queued from Python with C callbacks
- Library home/facets/favorites queue missing covers via the pool (non-blocking); sync Python fallback when the cdylib is absent
- `voxplayer/native_workers.py` bridge for the Python shell

### Changed
- ROADMAP Phase 2 marked done; Phase 3 (optional Zig) is next

## [1.4.0] - 2026-10-23

### Changed
- Playback engine rewritten onto the native C media core (python-vlc + system libvlc) with in-app window-ID video embed
- Volume 0–200% via core volume / media gain; install guidance and docs retargeted to the new engine

### Fixed
- Black / missing in-app video stage caused by unreliable prior embed path
- Play/pause race on load that left media stopped after open

## [1.3.3] - 2026-10-23

### Fixed
- In-app video embed: do not open an external video window; bind WID before loading video
- Seek scrubbing no longer freezes the UI on large jumps (deferred keyframe seek; exact on release)
- Torrent picker: select multiple files across folders; ROADMAP scrub of excluded-scope wording

### Changed
- ROADMAP: stronger native Rust/C/Zig migration stance for long-run performance

## [1.3.2] - 2026-10-23

### Fixed
- Volume **0%** no longer snaps back to 100% (`volume or 100` truthiness on engine setup; play-start timers re-assert engine volume instead of clobbering a fresh 0% set)
- Persisted 0% survives reload; mute and 100–200% restore from 0% unchanged

### Tests
- `tests/test_volume_zero.py` — UI `set_volume(0)` + native engine readback across play-start timers

## [1.3.1] - 2026-10-23

### Fixed
- native-engine startup segfault under non-C locales (`LC_NUMERIC=C` before engine init)
- Native-engine install dialog no longer cites third-party GitHub installation URLs

## [1.3.0] - 2026-10-23

### Added
- **Zone-aware drag-and-drop**: drop on Home/library grid → **index only**; drop on Now Playing / Up next / bottom transport → **add and play immediately**
- **Rust `vox_scan` native scanner** (`native/vox_scan`) with Python ctypes loader for parallel folder walks; Python walker remains if the `.so` is not built
- Clear **native-engine install guidance** on Linux / Windows / macOS when python-vlc or system libvlc is missing (`run.py` preflight + startup dialog)

### Changed
- **Native C media core is the only playback engine** — Qt Multimedia is no longer a playback fallback (PyQt6 remains the UI shell; `QVideoWidget` is an embed surface only)
- Volume **0–200%** and mute use engine-native native-engine properties only (no Pulse/`pactl` design path)
- Filter tabs **All / Video / Audio / Recent** use understated icon+text controls instead of heavy filled chips
- Home library and Up next **scrollbars** are wider, higher-contrast, and easier to grab on the dark theme
- Default logical volume for new installs is **100%**; engine label always reports native C core (embedded or audio path)
- ROADMAP expanded: native Rust/Zig/C phases, skin/daemon/podcast-like feeds, portable-player concepts, Android/GrapheneOS — without third-party brand names

### Fixed
- Volume slider and speaker mute fighting each other when the engine was on the old Qt path
- `run.py` ensuring the project `.venv` (with `python-vlc`) is the interpreter users actually launch

### Removed
- Silent fallback from the native engine failures to Qt Multimedia playback
- Recursive “accept drops everywhere” behavior that broke zone-specific drop routing

## [1.2.1] - 2026-10-23

### Changed
- Now Playing header keeps Expand / Minimize only in the ⋯ menu (standalone icon buttons removed)
- Up next **Clear** is an icon-only control with tooltip “Clear Up next and stop”
- Right-side **Queue** dock removed; Up next under Now Playing is the only queue UI
- Library facets: **Audio** shows Year / Genre / Artist; **Video** shows Movies / TV Shows; **Type** facet removed; All / Recent hide the facet row
- Save to playlist offers existing playlists plus “Create new…”
- `run.py` prefers the project `.venv` interpreter so torrent deps resolve consistently

### Fixed
- Favorites context menu shows **Remove from Favorites** when the item is already saved
- Named playlists appear as selectable chips in Favorites & playlists and open to their tracks
- Clearing Up next fully stops playback and resets Now Playing / transport title, art, and time

## [1.2.0] - 2026-10-23

### Added
- **Streaming-style Now Playing**: header with More menu, large rounded cover, click art to expand
- **Grid / List toggle** with responsive grid columns that reflow on resize
- **Library browse facets**: year, genre, artist, movies (chronological), TV by season
- **Favorites & local playlists** persisted under `~/.local/share/voxplayer/playlists/` (file paths)
- **System tray**: minimize / close-to-tray keeps audio and video playing; restore from tray
- **Modern About modal** with VoxPlayer branding, version, and copyright
- Up next: click to play, right-click remove, Clear Up next and stop, Add to queue from library

### Changed
- **Native C media core is the default engine** when available — reliable 0–200% volume without requiring `VOXPLAYER_ENGINE` or Pulse-only workarounds for the happy path
- **Audio no longer opens the empty center stage**; video stage shows for video playback or when the user expands Now Playing
- `qbittorrent-api` and `python-vlc` moved into **main install dependencies**
- Up next lives in the Now Playing rail

### Fixed
- Video poster/thumbnail capture skips near-black frames and retries multiple seek points
- Torrent import no longer fails with “qbittorrent-api not available” on a normal `pip install voxplayer`

## [1.1.1] - 2026-10-22

### Fixed
- **Volume accuracy**: Media Information reports the same 0–200% logical volume as the transport slider (no longer Qt’s clamped 0–100%)
- **Volume boost**: Qt path applies PipeWire/PulseAudio per-stream gain above 100%; native C core uses volume 0–200
- **Now Playing / transport art**: live video frame grabs while playing; ffmpeg/cache thumbnails for library cards and transport
- **Torrent gating**: reject non-media torrents (ISO/distro/archives) before add; re-check after client metadata

### Added
- Metadata enrichment via ffprobe/mutagen tags, MusicBrainz, optional AcoustID (`ACOUSTID_API_KEY`), optional TMDB (`TMDB_API_KEY`), Cover Art Archive
- Offline-first metadata: disk cache (`~/.cache/voxplayer/metadata/`), fetch-once per file identity, **View → Refresh Metadata** / library refresh
- Optional extras: `pip install "voxplayer[metadata]"`

## [1.1.0] - 2026-10-22

### Added
- **Modern shell**: left library rail, center home/stage, now-playing panel, bottom transport bar
- **VoxPlayer identity**: ember-on-charcoal theme (unique product look)
- **Home library grid** with All / Video / Audio / Recent filters and search
- **Playback engine abstraction** with Qt Multimedia default and optional native C media core (`pip install "voxplayer[native]"`)
- Hardware-decode hints for Qt FFmpeg (`QT_FFMPEG_DECODING_HW_DEVICE_TYPES`) and native-engine hardware decode when embedded

### Changed
- Root `app.py` is a thin launcher; packaged implementation remains `voxplayer/app.py`
- Default window size and layout oriented for the four-pane desktop shell
- ROADMAP updated for phased native-core migration

### Fixed
- Clearer engine status in the now-playing panel

## [1.0.4] - 2026-10-05

### Added
- **PyPI**: Published `voxplayer` 1.0.4 to [PyPI](https://pypi.org/project/voxplayer/) (`pip install voxplayer`)
- README PyPI badges and install path at the top of the project page

### Fixed
- **qBittorrent localhost**: Prefer unauthenticated loopback connects so a wrong `QB_PASSWORD` no longer triggers WebUI IP bans on `127.0.0.1`
- **Torrent add**: Treat newer `TorrentsAddedMetadata` WebAPI success responses as a successful add

## [1.0.3] - 2026-10-05

### Fixed
- **CI Lint**: Style flake8 report is advisory (critical undefined-name/syntax checks still hard-fail), matching black/mypy policy
- **Linux Build**: Replace obsolete `libgl1-mesa-glx` with Noble-compatible `libgl1`/`libegl1` packages in `build.yml`
- Trailing whitespace cleaned in `app.py` / `voxplayer/app.py` for cleaner diffs

## [1.0.2] - 2026-10-05

### Added
- Complete documentation kit under `docs/` (getting started, install, configuration, usage, CLI, API, architecture, troubleshooting, FAQ, examples)
- GitHub issue templates (bug, feature, docs) and pull request template

### Changed
- README and ROADMAP aligned with current product state (October 2026)
- Contact metadata standardized to `contact@voxhash.dev` / VoxHash Technologies
- `.gitignore` expanded for workstation scratch copies and common local junk

### Removed
- `DEVELOPMENT_GOALS.md` (superseded by `ROADMAP.md` and the docs kit)

### Fixed
- Support/docs links that pointed at a missing `docs/` tree

## [1.0.1] - 2026-03-12

### Added
- **CI/CD Pipeline**: Complete GitHub Actions workflows
  - Continuous Integration workflow with linting and testing across Python 3.8-3.12
  - Cross-platform build workflow (Windows, macOS, Linux)
  - Automated release workflow for version tags
  - CodeQL security analysis workflow
- **Documentation Files**:
  - `CODE_OF_CONDUCT.md` - Community code of conduct
  - `SECURITY.md` - Security policy and vulnerability reporting
  - `SUPPORT.md` - Support information and getting help
- **Repository Configuration**:
  - Comprehensive `.gitignore` with Python, Node.js, and build artifacts
  - `.gitattributes` for consistent line endings

### Changed
- **Documentation Restructure**: Updated all documentation files for consistency
  - `README.md` - Restructured with table of contents and improved organization
  - `CONTRIBUTING.md` - Streamlined with conventional commits and testing guidelines
  - `ROADMAP.md` - Simplified with quarterly milestones
  - `DEVELOPMENT_GOALS.md` - Organized with short-term and mid-term goals
- **Code Quality**:
  - Cleaned up duplicate and unused imports in `app.py`
  - Improved code formatting and consistency
- **Build Scripts**:
  - Updated `build_source.sh` to remove GITHUB_TOPICS.md references

### Removed
- `GITHUB_TOPICS.md` - Removed file and all references from documentation
- Duplicate imports (tempfile, os, shutil)
- Unused imports (threading, hashlib, urllib.parse, subprocess, asdict, and various PyQt6 components)

### Fixed
- Fixed duplicate imports in `app.py`
- **Volume Amplification**: Implemented true digital pre-amp for 0-200% volume boost
  - Direct sample multiplication (0.0-2.0x gain)
  - Proper clipping handling and user warnings
  - Consistent volume application across all audio output paths
- **Torrent Streaming**: Enhanced sequential download and buffering
  - Sequential piece downloading (0, 1, 2... n) for smooth playback
  - Intelligent buffering thresholds (10MB MP4, 20MB MKV)
  - File priority selection for optimal streaming
  - Real-time playback while downloading
  - qBittorrent API compatibility fixes
- **CI/CD**: Resolved Windows Unicode encoding errors
- **Code Quality**: Removed duplicate imports and improved error handling
- Removed unused PyQt6 imports (QSize, QMimeData, QFont, QColor, QPixmap, QProgressBar, QComboBox, QCheckBox, QSpinBox, QColorDialog, QAudioDevice)
- Fixed code formatting issues
- Removed duplicate blank lines

## [1.0.0] - 2024-12-19

### Added
- **Complete Media Player**: Ultra-compact design with professional UI
- **File Association Support**: Double-click any media file to open with VoxPlayer
- **Command-Line Support**: Direct file opening from command line
- **Advanced Playlist Management**: Smart playlist behavior with search and filtering
- **Torrent Streaming**: qBittorrent integration for streaming media
- **Auto-Update System**: GitHub-based update checking
- **Audio Device Selection**: Default or manual audio output
- **Professional Features**: Fullscreen mode, timeline preview, subtitle support
- **Cross-Platform Support**: Windows, macOS, and Linux distributions
- **Native Packaging**: Professional installers for all platforms
- **Source Distribution**: pip-installable Python package
- **Comprehensive Documentation**: Complete user and developer guides

### Core Features
- **Universal Format Support**: 15+ video and audio formats (MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V, MP3, FLAC, WAV, OGG, M4A, AAC, WMA)
- **Ultra-Compact Design**: Minimalist interface with maximum functionality
- **True Volume Amplification**: Up to 200% volume boost
- **Smart Playlist Behavior**: No auto-clearing, persistent playlist
- **Drag & Drop Support**: Files and folders from Windows Explorer
- **Real-Time Search**: Instant filtering within playlists
- **Import/Export**: M3U, PLS, XSPF, and text format support
- **Individual Item Control**: Remove specific items with X buttons
- **Visual Selection**: Clear indication of current playing item

### Advanced Features
- **Torrent Streaming**: qBittorrent integration for streaming
- **Auto-Update System**: GitHub-based update checking
- **Audio Device Selection**: Default or manual audio output
- **Fullscreen Mode**: Auto-hiding controls for immersive viewing
- **Timeline Preview**: Hover and drag preview on timeline
- **SRT Subtitle Support**: Built-in subtitle display
- **Snapshot Functionality**: Capture frames from videos
- **Context Menus**: Right-click options for advanced features

### User Experience
- **Dark Theme**: Professional dark interface
- **Keyboard Shortcuts**: 15+ shortcuts for efficient control
- **File Associations**: Professional Windows integration
- **Command-Line Interface**: Direct file opening support
- **Settings Menu**: Comprehensive configuration options
- **Help System**: Built-in help and keyboard shortcuts

### Technical Implementation
- **PyQt6 Framework**: Modern cross-platform GUI
- **FFmpeg Backend**: Professional media processing
- **Cross-Platform Build**: Automated build scripts for all platforms
- **Native Packaging**: Platform-specific installers and packages
- **File Associations**: Platform-specific integration
- **GitHub Integration**: Auto-update and release management
