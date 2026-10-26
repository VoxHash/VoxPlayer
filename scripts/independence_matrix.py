#!/usr/bin/env python3
"""Print the dependency independence matrix and enforce e2e gates."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    from voxplayer.engine.independence import (
        assert_e2e_independence_gates,
        build_independence_report,
    )

    report = build_independence_report()
    print(report.as_text())
    print()
    fails = assert_e2e_independence_gates()
    if fails:
        print("GATES FAIL:")
        for f in fails:
            print(f"  • {f}")
        return 1
    print("GATES PASS (current phase: libvlc required on desktop; python-vlc forbidden)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
