# Configuration

## In-app settings

Open **File → Settings** (or `Ctrl+,` when available in your build). Values persist via Qt `QSettings` under organization `VoxHash` / application `VoxPlayer`.

| Setting | Description | Default |
|---------|-------------|---------|
| Audio Output | Default or manual device | Default |
| Volume | Master volume (amplification up to 200%) | 50% |
| Theme | View → Theme (Ember / Midnight / Slate / Graphite + `~/.config/voxplayer/themes/*.json`) | Ember |
| Auto-Update | Check GitHub for updates | Enabled |
| Update Channel | Stable or Beta | Stable |

## Environment variables

No environment variables are required for local file playback.

| Variable | Required for | Default | Notes |
|----------|--------------|---------|-------|
| `QB_HOST` | Torrent streaming | `localhost:8080` | Host:port of qBittorrent Web UI |
| `QB_USERNAME` | Torrent streaming (if auth enabled) | empty | Web UI username |
| `QB_PASSWORD` | Torrent streaming (if auth enabled) | empty | Web UI password — do not commit |
| `QT_QPA_PLATFORM` | Headless CI / tests | unset | Use `offscreen` without a display |
| `QT_LOGGING_RULES` | Log noise control | unset | Launcher sets FFmpeg/future rules |
| `PYTHONIOENCODING` | Windows CI | unset | Set `utf-8` if Unicode console issues appear |

Example:

```bash
export QB_HOST=127.0.0.1:8080
export QB_USERNAME=admin
export QB_PASSWORD='your-webui-password'
python app.py
```

## qBittorrent Web UI

First-run in the app: **Media → Torrent → Web UI Setup Guide…** (also shown once before the first magnet/torrent open). VoxPlayer never ships default passwords.

1. Start qBittorrent (or `qbittorrent-nox --webui-port=8080`)
2. Enable Web UI in preferences
3. Prefer “Bypass authentication for clients on localhost”, or set a username/password you control
4. Export matching `QB_*` variables before launching VoxPlayer when auth is required
5. Too many failed logins can temporarily ban your IP — clear bans in qBittorrent if auth suddenly returns 403

## Secrets

Never commit `.env` files or real Web UI passwords. `.gitignore` already excludes `.env*` and torrent/media caches.

## Playback engine

**Native C media core is the only playback engine** (`python-vlc` + system libvlc). Volume 0–200% and mute use native-engine properties. There is no Qt Multimedia playback path — missing native C media core exits with install instructions.

Prefer X11/XWayland (`QT_QPA_PLATFORM=xcb` when `DISPLAY` is set) for WID video embed. On pure Wayland without a libvlc Wayland surface API, audio volume still works; embed may be limited.

| Variable | Default | Description |
|----------|---------|-------------|
| `VOXPLAYER_EMBED` | `auto` | `auto` / `xcb` / `wayland` — embed preference |
| `VOXPLAYER_FORCE_WAYLAND` | unset | Set to `1` to skip X11 preference under Wayland |
| `VOXPLAYER_KEEP_QPA` | unset | Set to `1` to leave `QT_QPA_PLATFORM` unchanged |
| `VOXPLAYER_TORRENT_BUFFER_MB` | unset | Override torrent startup buffer (MiB) |
| `VOXPLAYER_TORRENT_BUFFER_PCT` | unset | Override buffer as percent of file size (0–100) |
| `VOXPLAYER_DAEMON` | `1` | Localhost HTTP control daemon (`0` to disable) |
| `VOXPLAYER_DAEMON_HOST` | `127.0.0.1` | Bind address (non-loopback needs `VOXPLAYER_DAEMON_ALLOW_LAN=1`) |
| `VOXPLAYER_DAEMON_PORT` | `17890` | Control daemon port; remotes: `voxplayer-tui`, browser `/ui`, Android companion |
| `VOXPLAYER_DAEMON_ALLOW_LAN` | unset | Set `1` to allow non-loopback binds for multi-room / phone companion |
| (CLI) `voxplayer-lan-bypass` | — | Install/remove RFC1918 routes via the physical LAN NIC so VPN kill-switches do not black-hole companion Wi‑Fi |
| (CLI) `voxplayer-usb-bridge` | — | Collapse duplicate `adb` servers and refresh `adb reverse` for USB companion e2e |
| `VOXPLAYER_DISCOVERY` | `1` | UDP LAN announce for Connect discovery (`0` to disable) |
| `VOXPLAYER_DISCOVERY_PORT` | `17891` | UDP port companions scan for desktop announces |
| `VOXPLAYER_BT` | `1` | Bluetooth RFCOMM control server when adapter is available (`0` to disable) |
| `VOXPLAYER_BT_CHANNEL` | `5` | RFCOMM channel for the VoxPlayer control profile (SPP UUID) |
| `VOXPLAYER_DISABLE_MPRIS` | unset | Set to `1` to disable MPRIS2 on Linux |
| `ACOUSTID_API_KEY` | unset | Optional AcoustID client key for audio fingerprint lookup |
| `TMDB_API_KEY` | unset | Optional TMDB key for video title/poster enrichment |
| `FPCALC` | `fpcalc` | Path to AcoustID `fpcalc` binary when using fingerprinting |

System package: install `vlc` / libvlc from your distro (see [installation.md](installation.md)).

### Metadata enrichment (offline-first)

Playback, library load, and the UI never depend on the network.

| Mode | Behavior |
|------|----------|
| Offline | Local tags / ffprobe / filename / embedded or generated thumbnails only. No error dialogs. |
| Online | Remote lookup at most **once per file** (identity = path + size + mtime). Results cached under `~/.cache/voxplayer/metadata/`. |
| Refresh | **View → Refresh Metadata** (current item) or **Refresh Metadata for Library** re-fetches when online. |

Pipeline when online (and not yet cached):

1. MusicBrainz recording search (no key; polite User-Agent required)
2. Cover Art Archive for release front covers
3. AcoustID when `ACOUSTID_API_KEY` is set (`pip install "voxplayer[metadata]"` + `fpcalc`)
4. TMDB multi-search when `TMDB_API_KEY` is set

Local embedded tags are shown immediately; network data fills empty fields asynchronously and does not wipe good local tags unless you refresh.

Store keys only in the environment or a local gitignored `.env`. Never commit API keys.

```bash
export ACOUSTID_API_KEY='your-acoustid-app-key'
export TMDB_API_KEY='your-tmdb-v3-key'
pip install "voxplayer[metadata]"
```

### Torrent media gate

Only torrents whose contents look like a media library (common audio/video extensions and/or playlist files such as `.m3u` / `.cue`) are accepted. ISO/distro/installer torrents are rejected with a clear error before (and after) add.
