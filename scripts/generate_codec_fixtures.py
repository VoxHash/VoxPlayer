#!/usr/bin/env python3
"""Write ``fixtures/codecs/`` samples and print the Desktop FOSS matrix."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    from voxplayer.codec_fixtures import ensure_repo_fixtures

    report = ensure_repo_fixtures()
    print("\n".join(report.summary_lines()))
    return 0 if report.required_ok() else 1


if __name__ == "__main__":
    raise SystemExit(main())
