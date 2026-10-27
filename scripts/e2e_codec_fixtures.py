#!/usr/bin/env python3
"""E2E: H.264 / HEVC / AV1 / Opus decode fixtures on Desktop FOSS libav."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    from voxplayer.codec_fixtures import ensure_repo_fixtures
    from voxplayer.media import libav_io

    ok, detail = libav_io.available()
    if not ok:
        print(f"SKIP need voxplayer[libav]: {detail}")
        return 0

    report = ensure_repo_fixtures()
    for line in report.summary_lines():
        print(line)

    # Soft codecs may skip if host lacks encoder (e.g. CI without libx265)
    soft = {"hevc", "av1"}
    hard_fail = False
    for key, result in report.results.items():
        if result.skipped and key in soft:
            print(f"OK soft-skip {key}: {result.error}")
            continue
        if result.skipped and key not in soft:
            print(f"FAIL required codec skipped: {key} — {result.error}")
            hard_fail = True
            continue
        if result.encoded and not result.decoded:
            print(f"FAIL {key} encoded but FOSS decode failed")
            hard_fail = True
            continue
        if result.decoded:
            print(f"OK {key} decode ({result.decoder})")

    if hard_fail or not report.required_ok():
        print("E2E CODEC FIXTURES FAIL")
        return 1
    print("E2E CODEC FIXTURES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
