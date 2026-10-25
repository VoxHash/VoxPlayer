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

On Meta Quest, the companion launches in the common Horizon OS 2D panel size (**1024×640 dp** by default, resizable). Wide layouts show the desktop-style Home grid + Now Playing column.

**Background playback:** on-device Media3 audio runs in a `mediaPlayback` foreground service with a system media notification. Force-stop or strict battery limits can still stop playback; there is no proprietary keep-alive SDK.

**Widget:** Add the VoxPlayer widget from the launcher — play/pause / prev / next without opening the app (no Google Glance / GMS).

**Share card:** Now Playing → Share card builds an offline PNG (title/artist/album/art) and opens the system share sheet — no cloud.

**Listening stats:** Home → Week / Month — on-device listen counts, unique tracks, and top artist (no scrobbling / cloud).

**Sound / EQ:** Now Playing → Sound output lists sinks by group (This device / Wired / Bluetooth / …) with a clear Routing line; Equalizer presets show selection + short description (AOSP effect, no GMS).

**M3U:** Now Playing → Export queue M3U; Lists → Import M3U / open a folder → Export M3U. Offline only (FileProvider share + SAF); remote http(s) lines are skipped.

**DLNA cast:** Now Playing → Enable DLNA → Scan → Cast now. Uses FOSS UPnPCast on the LAN only — no Google Cast / GMS.

**Search:** Home search field filters by title / artist / album (also applies to Recent / Top / Week / Month).

**Artwork:** Home grid and Recent/Top cards load MediaStore thumbnails / album art offline (no CDN).

**Quest / foldable:** Short 2D panels and multi-window use compact chrome; fold hinges get side padding. Playback stays in the media session service across resize (no GMS).

**Driving layout:** On wide landscape (≥900dp) the Local tab switches to large transport + Recent (no Google Auto).

**AVRCP / car displays:** Local library items advertise title, artist·album subtitle, duration, and album-art URI on the Media3 session for Bluetooth head units (no Google Automotive).

**Transitions:** Now Playing Fade-in (soft volume ramp on auto next; Short / Med / Long / Soft length) and Skip silence (ExoPlayer). Mixed audio/video playlists keep same-kind continuity.

**Speed:** Now Playing → Speed — 0.75×–2× playback rate (Media3; useful for podcasts).

**Resume:** Leaving a track mid-way remembers position on-device; reopening seeks there (separate from Bookmarks). Now Playing shows “Resumed from …” with Forget.

**A–Z index:** Home library is sorted by title with letter headers; tap a letter on the right rail to jump.

**Theme:** Header → Theme cycles Dark / Light / System (ember charcoal or warm paper; follows OS when System).

**Seek:** Now Playing scrubber — drag or tap to seek; shows a live preview while dragging.

**Notification:** System media controls expose ±15s, Previous/Next, Bookmark, and Speed cycle (overflow). Tap the notification to return to VoxPlayer.

**Status chips:** Now Playing shows Queue n/N, Out: route, Sleep m:ss (accent when relevant) plus Fade / Skip silence / Speed / EQ / Shuffle / Repeat chips; tap a chip to jump to that section; toggles flash a short status toast.

**Route fallback:** If a forced headset/BT sink disconnects, routing returns to System default with a toast; loud playback is soft-ducked to 40% to avoid speaker blast.

**Clear queue:** Up next → Clear queue (tap twice to confirm). Undo restores the last cleared queue while the toast window is open.

**Remove from queue:** Up next row ✕ removes the item; Undo re-inserts it at the same index for a few seconds.

**Reorder queue:** Drag the ≡ handle on an Up next row (haptic on grab / each step), or use the arrow buttons. TalkBack announces position, title, and actions.

**Jump to playing:** Up next auto-scrolls to the current track when it changes; use Jump to playing after scrolling away.

**Empty library:** Home shows contextual tips when a filter or search has no rows (Open file / permissions / history facets).

**Clear search:** Home search field shows ✕ when a query is active.

**Remember Home:** Filter chip, search query, and A–Z section letter persist across process death (on-device prefs).

**Pull to refresh:** On Home, pull down to reload MediaStore + local history / lists.

**Lyrics:** Place `Song.lrc` (or `.srt` / `.vtt` / `.txt`) beside `Song.mp3`; Now Playing shows timed or plain lines. No online lyrics fetch.

**Lists:** Home Lists chip — smart lists (New / Recent / Top / Short ≤3 min) and manual folders; Add Now Playing into a folder. Local JSON only.

**Play history:** Local JSON only — after ~3s of play, Recently / Most-played facets on Home (no scrobble / cloud). Clear history from the facet header.

**Sleep timer / bookmarks:** Now Playing sleep chips (15–90 min) fade then pause in the media session service. Per-URI bookmarks autosave while playing and can be resumed offline — no cloud.

**Headset / Quest audio:** Bluetooth headset AVRCP uses Media3 media-button preferences (±15s seek). When a preferred sink disconnects, playback falls back to system default; Quest panel resume re-applies volume/EQ/route. No GMS Auto.

**Sound output / EQ:** Now Playing lists `AudioManager` sinks (speaker, wired, Bluetooth A2DP, USB, HDMI) and routes via Media3 `setPreferredAudioDevice`. AOSP `Equalizer` presets attach to the playback session; GrapheneOS may omit effects — Off still works. No GMS.

**Volume 0–200%:** local playback uses the same logical scale as desktop (mute + 0–200). Above 100% uses AOSP `LoudnessEnhancer` (no proprietary boost SDK); GrapheneOS may omit the effect — 0–100% still applies.

**Repeat / shuffle / queue reorder:** transport and Now Playing expose Media3 repeat (off/all/one) and shuffle; Up Next supports move up/down and remove. Modes persist in app prefs.

**Gapless local queues:** tapping a library item loads a Media3 playlist from the filtered library (same audio/video kind under All). Transport prev/next skips tracks; encoder delay/padding enables gapless where the file provides it.

**Playback resumption:** last local URI + position are stored in app prefs. After process death, headset / media-key play can restart via Media3 `MediaButtonReceiver` + `onPlaybackResumption` if the URI is still readable. Stop clears the store.

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
