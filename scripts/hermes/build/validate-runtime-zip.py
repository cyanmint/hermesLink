#!/usr/bin/env python3
"""Validate that hermesrt.zip contains only the Python runtime payload."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path


REQUIRED_ENTRIES = {
    "timestamp.txt",
    "hermes/hermes_cli/main.py",
    "python/encodings/__init__.py",
    "python/site-packages/openai/__init__.py",
    "python/site-packages/openai/lib/__init__.py",
    "python/site-packages/openai/lib/azure.py",
}
NATIVE_SUFFIXES = {
    ".a",
    ".bundle",
    ".dll",
    ".dylib",
    ".exe",
    ".framework",
    ".o",
    ".obj",
    ".pyd",
    ".so",
    ".wasm",
}
NATIVE_MAGICS = (
    b"\x7fELF",
    b"MZ",
    b"\x00asm",
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
)


def validate_archive(path: str | Path) -> int:
    """Raise ValueError unless *path* is an intact, native-free Hermes runtime ZIP."""
    archive_path = Path(path)
    try:
        archive = zipfile.ZipFile(archive_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"invalid Hermes runtime ZIP: {exc}") from exc

    with archive:
        corrupt_entry = archive.testzip()
        if corrupt_entry is not None:
            raise ValueError(f"corrupt ZIP entry: {corrupt_entry}")

        names = set(archive.namelist())
        missing = sorted(REQUIRED_ENTRIES - names)
        if missing:
            raise ValueError(f"missing required runtime entries: {', '.join(missing)}")

        timestamps = [info for info in archive.infolist() if info.filename == "timestamp.txt"]
        if len(timestamps) != 1 or timestamps[0].compress_type != zipfile.ZIP_STORED:
            raise ValueError("timestamp.txt must be a single stored ZIP entry")
        try:
            timestamp_text = archive.read(timestamps[0]).decode("ascii").strip()
            timestamp = int(timestamp_text)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("timestamp.txt must contain a Unix timestamp in milliseconds") from exc
        if not timestamp_text.isdecimal() or not 0 < timestamp <= 2**63 - 1:
            raise ValueError("timestamp.txt must contain a positive Unix timestamp in milliseconds")

        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if info.compress_type != zipfile.ZIP_STORED:
                raise ValueError(f"runtime ZIP entries must use ZIP_STORED: {name}")
            lowered = name.lower()
            suffix = Path(lowered).suffix
            if suffix in NATIVE_SUFFIXES or any(
                part.endswith((".framework", ".bundle")) for part in lowered.split("/")
            ):
                raise ValueError(f"native runtime file is forbidden in hermesrt.zip: {name}")
            with archive.open(info) as member:
                magic = member.read(8)
            if any(magic.startswith(signature) for signature in NATIVE_MAGICS):
                raise ValueError(f"native binary payload is forbidden in hermesrt.zip: {name}")

        return len(names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args(argv)
    try:
        entries = validate_archive(args.archive)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Validated pure-Python Hermes runtime ZIP: {args.archive} ({entries} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
