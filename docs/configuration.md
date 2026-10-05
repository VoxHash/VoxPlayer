# Configuration

## In-app settings

Open **File → Settings** (or `Ctrl+,` when available in your build). Values persist via Qt `QSettings` under organization `VoxHash` / application `VoxPlayer`.

| Setting | Description | Default |
|---------|-------------|---------|
| Audio Output | Default or manual device | Default |
| Volume | Master volume (amplification up to 200%) | 50% |
| Theme | UI theme | Dark |
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

1. Start qBittorrent (or `qbittorrent-nox --webui-port=8080`)
2. Enable Web UI in preferences
3. Set a username/password you control
4. Export matching `QB_*` variables before launching VoxPlayer
5. Too many failed logins can temporarily ban your IP — clear bans in qBittorrent if auth suddenly returns 403

## Secrets

Never commit `.env` files or real Web UI passwords. `.gitignore` already excludes `.env*` and torrent/media caches.
