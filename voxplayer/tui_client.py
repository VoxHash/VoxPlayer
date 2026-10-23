"""Terminal UI (and one-shot CLI) for the localhost control daemon.

Requires a running VoxPlayer desktop session with the daemon enabled
(default ``127.0.0.1:17890``).

Keys (TUI)::

    Space  play/pause
    n / p  next / previous
    s      stop
    + / -  volume ±5
    ← / →  seek ±5s
    o      open path
    r      refresh
    q      quit
"""

from __future__ import annotations

import argparse
import curses
import os
import sys
import time
from typing import Any, Dict, Optional

from .daemon_client import DaemonClient, default_base_url


def _fmt_ms(ms: int) -> str:
    try:
        ms = max(0, int(ms))
    except (TypeError, ValueError):
        return "0:00"
    sec = ms // 1000
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _basename(path: str) -> str:
    if not path:
        return "(nothing loaded)"
    return os.path.basename(path) or path


def run_once(client: DaemonClient, action: str, args: argparse.Namespace) -> int:
    action = action.lower().strip()
    mapping = {
        "status": client.status,
        "play": client.play,
        "pause": client.pause,
        "playpause": client.playpause,
        "stop": client.stop,
        "next": client.next,
        "previous": client.previous,
        "root": client.root,
    }
    if action in mapping:
        result = mapping[action]()
    elif action == "volume":
        if args.percent is None:
            print("volume requires --percent", file=sys.stderr)
            return 2
        result = client.volume(args.percent)
    elif action == "seek":
        if args.ms is None and args.relative_ms is None:
            print("seek requires --ms or --relative-ms", file=sys.stderr)
            return 2
        result = client.seek(ms=args.ms, relative_ms=args.relative_ms)
    elif action == "open":
        if not args.path:
            print("open requires --path", file=sys.stderr)
            return 2
        result = client.open_path(args.path)
    else:
        print(f"unknown action: {action}", file=sys.stderr)
        return 2
    import json

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", True) and "error" not in result else 1


def _draw(stdscr, client: DaemonClient, status: Dict[str, Any], msg: str) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    title = "VoxPlayer TUI — control daemon"
    base = client.base_url.rstrip("/")
    playing = "PLAYING" if status.get("playing") else "PAUSED"
    path = _basename(str(status.get("path") or ""))
    pos = _fmt_ms(int(status.get("position_ms") or 0))
    dur = _fmt_ms(int(status.get("duration_ms") or 0))
    vol = int(status.get("volume_percent") or 0)
    err = status.get("error")

    lines = [
        title[: max(0, w - 1)],
        f"Daemon: {base}"[: max(0, w - 1)],
        "",
        f"[{playing}]  {path}"[: max(0, w - 1)],
        f"{pos} / {dur}   vol {vol}%"[: max(0, w - 1)],
        f"shuffle={status.get('shuffle')}  repeat={status.get('repeat')}  v{status.get('version', '?')}"[
            : max(0, w - 1)
        ],
        "",
        "Space play/pause  n/p next/prev  s stop  +/- vol  ←/→ seek  o open  r refresh  q quit"[
            : max(0, w - 1)
        ],
    ]
    if err:
        lines.append(f"ERROR: {err}"[: max(0, w - 1)])
    if msg:
        lines.append(msg[: max(0, w - 1)])

    for i, line in enumerate(lines):
        if i >= h - 1:
            break
        try:
            stdscr.addstr(i, 0, line)
        except curses.error:
            pass
    stdscr.refresh()


def _prompt_path(stdscr) -> Optional[str]:
    curses.echo()
    curses.curs_set(1)
    h, w = stdscr.getmaxyx()
    stdscr.addstr(h - 1, 0, "Open path: ".ljust(w - 1)[: w - 1])
    stdscr.move(h - 1, 11)
    try:
        raw = stdscr.getstr(h - 1, 11, max(8, w - 12))
        text = raw.decode("utf-8", errors="replace").strip() if raw else ""
    except Exception:
        text = ""
    curses.noecho()
    curses.curs_set(0)
    return text or None


def run_tui(client: DaemonClient) -> int:
    def _main(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(400)
        msg = ""
        status: Dict[str, Any] = {}
        last_poll = 0.0
        while True:
            now = time.time()
            if now - last_poll >= 0.4:
                status = client.status()
                last_poll = now
            _draw(stdscr, client, status, msg)
            try:
                ch = stdscr.getch()
            except curses.error:
                ch = -1
            if ch < 0:
                continue
            msg = ""
            if ch in (ord("q"), ord("Q"), 27):
                break
            if ch in (ord(" "),):
                client.playpause()
            elif ch in (ord("n"), ord("N")):
                client.next()
            elif ch in (ord("p"), ord("P")):
                client.previous()
            elif ch in (ord("s"), ord("S")):
                client.stop()
            elif ch in (ord("+"), ord("=")):
                vol = int(status.get("volume_percent") or 50) + 5
                client.volume(min(200, vol))
            elif ch in (ord("-"), ord("_")):
                vol = int(status.get("volume_percent") or 50) - 5
                client.volume(max(0, vol))
            elif ch == curses.KEY_LEFT:
                client.seek(relative_ms=-5000)
            elif ch == curses.KEY_RIGHT:
                client.seek(relative_ms=5000)
            elif ch in (ord("o"), ord("O")):
                path = _prompt_path(stdscr)
                if path:
                    result = client.open_path(path)
                    msg = result.get("error") or f"opened {path}"
            elif ch in (ord("r"), ord("R")):
                status = client.status()
                msg = "refreshed"
            last_poll = 0.0
        return 0

    return curses.wrapper(_main)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="voxplayer-tui",
        description="TUI / CLI remote for the VoxPlayer control daemon",
    )
    p.add_argument(
        "--url",
        default=None,
        help=f"Daemon base URL (default {default_base_url()})",
    )
    p.add_argument(
        "action",
        nargs="?",
        default=None,
        help="One-shot action: status, play, pause, playpause, stop, next, previous, volume, seek, open, root",
    )
    p.add_argument("--percent", type=int, default=None, help="Volume percent for 'volume'")
    p.add_argument("--ms", type=int, default=None, help="Absolute seek ms")
    p.add_argument("--relative-ms", type=int, default=None, dest="relative_ms")
    p.add_argument("--path", default=None, help="Media path for 'open'")
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    client = DaemonClient(base_url=args.url)
    if args.action:
        return run_once(client, args.action, args)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("TUI needs a terminal; pass an action for one-shot CLI use.", file=sys.stderr)
        return 2
    return run_tui(client)


if __name__ == "__main__":
    raise SystemExit(main())
