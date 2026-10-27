#!/usr/bin/env python3
"""E2E: standing codec policy #82 — no in-tree x264/x265 source trees."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    from voxplayer.engine.codec_policy import (
        POLICY_ID,
        POLICY_VERSION,
        scan_forbidden_codec_trees,
        policy_blurb,
    )

    report = scan_forbidden_codec_trees(ROOT)
    print("\n".join(report.summary_lines()))
    if POLICY_ID != "voxplayer-codec-policy-82" or not POLICY_VERSION:
        print("FAIL policy id/version missing")
        return 1
    if "x264" not in policy_blurb().lower():
        print("FAIL policy blurb missing x264 non-goal")
        return 1
    if not report.ok:
        print("E2E CODEC POLICY FAIL")
        return 1
    print("E2E CODEC POLICY PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
