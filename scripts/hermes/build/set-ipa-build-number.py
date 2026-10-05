#!/usr/bin/env python3
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Set the iOS app's CFBundleVersion during final IPA assembly."""

from __future__ import annotations

import plistlib
import re
import sys
from pathlib import Path


def set_build_number(info_plist: Path, build_number: str) -> None:
    if not re.fullmatch(r"[0-9]+", build_number) or int(build_number) < 1:
        raise ValueError("build number must be a positive integer")

    raw_plist = info_plist.read_bytes()
    plist_format = plistlib.FMT_BINARY if raw_plist.startswith(b"bplist00") else plistlib.FMT_XML
    info = plistlib.loads(raw_plist)
    if not isinstance(info, dict):
        raise ValueError("app Info.plist must contain a dictionary")
    if "CFBundleVersion" not in info:
        raise ValueError("app Info.plist is missing CFBundleVersion")

    info["CFBundleVersion"] = build_number
    info_plist.write_bytes(plistlib.dumps(info, fmt=plist_format, sort_keys=False))


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: set-ipa-build-number.py <app-Info.plist> <build-number>", file=sys.stderr)
        return 2
    try:
        set_build_number(Path(argv[1]), argv[2])
    except (OSError, plistlib.InvalidFileException, ValueError) as exc:
        print(f"cannot set IPA build number: {exc}", file=sys.stderr)
        return 1
    print(f"Set CFBundleVersion to {argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
