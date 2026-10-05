# Example 01 — Play a local video

## Goal

Open a real MP4 from the command line and confirm the player loads it.

## Steps

```bash
cd /path/to/VoxPlayer
source .venv/bin/activate
python app.py "/path/to/your/video.mp4"
```

## Expected

- Window title: `your-video.mp4 - VoxPlayer`
- Status bar shows loaded file size and extension
- Space toggles play/pause

## Headless smoke check

```bash
QT_QPA_PLATFORM=offscreen python test.py
```
