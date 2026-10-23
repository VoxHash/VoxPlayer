# CLI

## Launchers

```bash
python app.py
python app.py "/absolute/or/relative/path/to/media.mp4"
python run.py
voxplayer   # after pip install
```

`run.py` sets quieter Qt logging rules, then calls `app.main()`.

## Arguments

| Argument | Behavior |
|----------|----------|
| (none) | Open empty player window |
| `<media-path>` | If the file exists and the extension is supported, load it on startup |
| missing path | Warning on stderr; player still opens |
| unsupported extension | Warning on stderr; path ignored |

Torrent files (`.torrent`) are **not** accepted as the CLI media argument. Open them from the UI after configuring qBittorrent.

## Control daemon remotes (TUI / browser)

With the desktop app running and the daemon enabled (default `127.0.0.1:17890`):

```bash
voxplayer-tui                 # interactive curses remote
voxplayer-ctl status          # one-shot JSON (alias of voxplayer-tui)
voxplayer-ctl playpause
voxplayer-ctl volume --percent 80
voxplayer-ctl seek --relative-ms 5000
voxplayer-ctl open --path /path/to/media.mp4
```

Browser remote (same JSON API; CORS enabled for external hosts / future WASM):

- Same-origin: open `http://127.0.0.1:17890/ui/` while the player is running
- Packaged files: `voxplayer/web_client/index.html` + `app.js`

Override target with `--url` or `VOXPLAYER_DAEMON_HOST` / `VOXPLAYER_DAEMON_PORT`.

## Android / GrapheneOS companion

Build the debug APK (JDK 17 + Android SDK):

```bash
export JAVA_HOME="${JAVA_HOME:-$HOME/.local/jdk-17}"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Android/Sdk}"
cd android && ./gradlew :app:assembleDebug
```

Trusted LAN: set `VOXPLAYER_DAEMON_ALLOW_LAN=1` and `VOXPLAYER_DAEMON_HOST=0.0.0.0` on the desktop. The app’s **Connect** sheet discovers the PC on Wi‑Fi via UDP port `17891` (or enter host/port manually). Paired Bluetooth devices can use the RFCOMM control profile (`VOXPLAYER_BT=1`, channel 5) when Wi‑Fi is unavailable. On-device audio/video plays locally with Media3 without a PC. Use **Sync playlists & podcasts** on the Desktop tab to pull `GET /playlists` and `GET /podcasts` into on-device cache.

When a desktop VPN (e.g. ProtonVPN) steals RFC1918 routes, keep LAN local:

```bash
voxplayer-lan-bypass status
sudo voxplayer-lan-bypass on --prefix 192.168.68.0/24   # extra home subnet if needed
```

USB without Wi‑Fi (also resets duplicate `adb` servers that hide devices):

```bash
voxplayer-usb-bridge reset
voxplayer-usb-bridge probe --serial <SERIAL>
adb -s <SERIAL> install -r android/app/build/outputs/apk/debug/app-debug.apk
adb -s <SERIAL> shell am start -n dev.voxhash.voxplayer.companion.debug/dev.voxhash.voxplayer.companion.MainActivity \
  --es host 127.0.0.1 --es port 17890 --ez autoconnect true
```

## Useful environment flags

```bash
QT_QPA_PLATFORM=offscreen python test.py
QT_LOGGING_RULES='qt.multimedia.ffmpeg.debug=false' python app.py
```
