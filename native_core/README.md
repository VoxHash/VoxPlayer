# native_core (staged desktop media core)

This directory holds a **staged** copy of the native C media core (libvlc +
plugins) used for:

- Desktop e2e that proves playback can load **without** system `/usr/lib/libvlc*`
- PyInstaller / CI bundles (`VOXPLAYER_NATIVE_CORE` / repo `native_core/`)

## Stage from the host

```bash
.venv/bin/python packaging/stage_native_core.py --force
.venv/bin/python scripts/e2e_native_core_bundle.py
```

Requires a system VLC / libvlc install on the build host (see
`packaging/install_native_core_*`). Staged binaries are **gitignored** — only
this README is committed.

## Runtime

`voxplayer.native_core_paths` discovers this tree automatically in a source
checkout. Override with `VOXPLAYER_NATIVE_CORE=/path/to/tree`.
