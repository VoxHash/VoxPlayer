"""Standing codec policy (ROADMAP #82) — wrap FOSS / MediaCodec; never invent x264/x265.

Machine-checkable: refuse vendored in-tree H.264/H.265 codec *source trees*.
Using host FOSS libs via PyAV/ffmpeg for fixtures or decode is allowed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

POLICY_ID = "voxplayer-codec-policy-82"
POLICY_VERSION = "1.0.0"

# Exact directory basenames that indicate a vendored greenfield / upstream codec tree.
FORBIDDEN_DIR_NAMES = frozenset(
    {
        "x264",
        "x265",
        "libx264",
        "libx265",
        "openh264",
        "x264-src",
        "x265-src",
    }
)

# Only flag forbidden names under these top-level path prefixes (repo-relative).
WATCH_ROOTS = (
    "native",
    "third_party",
    "third-party",
    "vendor",
    "vendored",
    "codecs",
    "src",
    "c",
    "cpp",
    "cxx",
    "crates",
)

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "build",
        "dist",
        "target",  # Rust/Zig build output
        "native_core",  # staged prebuilt libvlc plugins — not source invention
        ".gradle",
        ".idea",
        "android",  # MediaCodec wraps platform; no x264 trees expected; skip huge trees
    }
)

POLICY_LINES: Tuple[str, ...] = (
    "Non-goal: do not invent or vendor in-tree H.264/x264/H.265/x265 source trees.",
    "Desktop decode: wrap system/bundled libvlc and/or linked FOSS libav (PyAV).",
    "Android/Quest/GrapheneOS: wrap Media3 → MediaCodec only (no GMS decode SDK).",
    "Host FOSS libs for fixtures/decode (libx264/libx265/dav1d/opus via PyAV) are allowed.",
    "Staged native_core/ prebuilt plugins are packaging, not greenfield codecs.",
    "Never reintroduce python-vlc as the decode API.",
)


@dataclass
class CodecPolicyReport:
    policy_id: str = POLICY_ID
    policy_version: str = POLICY_VERSION
    repo_root: str = ""
    violations: List[str] = field(default_factory=list)
    scanned_dirs: int = 0

    @property
    def ok(self) -> bool:
        return not self.violations

    def summary_lines(self) -> List[str]:
        lines = [
            f"Codec policy {self.policy_id} v{self.policy_version}",
            f"Root: {self.repo_root or '(unset)'}",
            f"Scanned dirs: {self.scanned_dirs}",
            "",
            "Standing rules:",
        ]
        for p in POLICY_LINES:
            lines.append(f"  • {p}")
        lines.append("")
        if self.ok:
            lines.append("OK — no forbidden in-tree codec source trees found.")
        else:
            lines.append("FAIL — forbidden paths:")
            for v in self.violations:
                lines.append(f"  • {v}")
        lines.append("")
        lines.append("See docs/codec_policy.md")
        return lines

    def as_text(self) -> str:
        return "\n".join(self.summary_lines())


def repo_root_from_here() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    # voxplayer/engine → repo root
    return os.path.abspath(os.path.join(here, "..", ".."))


def _is_watched(rel: str) -> bool:
    rel = rel.replace("\\", "/").lstrip("./")
    if not rel:
        return False
    top = rel.split("/", 1)[0]
    return top in WATCH_ROOTS


def scan_forbidden_codec_trees(root: Optional[str] = None) -> CodecPolicyReport:
    """Walk the repo and flag vendored x264/x265-style source directories."""
    root = os.path.abspath(root or repo_root_from_here())
    report = CodecPolicyReport(repo_root=root)
    if not os.path.isdir(root):
        report.violations.append(f"repo root missing: {root}")
        return report

    for dirpath, dirnames, _filenames in os.walk(root):
        # prune
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".")]
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        report.scanned_dirs += 1

        for name in list(dirnames):
            child_rel = os.path.join(rel_dir, name) if rel_dir else name
            child_rel = child_rel.replace("\\", "/")
            if name.lower() in FORBIDDEN_DIR_NAMES and _is_watched(child_rel):
                report.violations.append(
                    f"forbidden codec source tree: {child_rel}/ "
                    f"(wrap FOSS/MediaCodec — do not vendor {name})"
                )
                dirnames.remove(name)  # no need to descend
    return report


def assert_codec_policy(root: Optional[str] = None) -> List[str]:
    """Return failure strings; empty means policy gates passed."""
    report = scan_forbidden_codec_trees(root)
    return list(report.violations)


def policy_blurb() -> str:
    return "\n".join(POLICY_LINES)
