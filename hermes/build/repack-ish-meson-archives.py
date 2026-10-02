#!/usr/bin/env python3
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Repackage Linux-generated iSH archives in Apple's static-library format."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ARCHIVES = ("deps/liblinux.a", "libfakefs.a", "libish_emu.a")


def repack_archive(archive: Path, llvm_ar: str, libtool: str) -> None:
    members = subprocess.run(
        [llvm_ar, "t", str(archive)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if not members:
        raise ValueError(f"Linux iSH archive is empty: {archive}")

    with tempfile.TemporaryDirectory(prefix=".ish-archive-", dir=archive.parent) as temp_dir:
        temp_path = Path(temp_dir)
        subprocess.run(
            [llvm_ar, "x", str(archive)],
            check=True,
            cwd=temp_path,
            capture_output=True,
            text=True,
        )
        objects = sorted(path for path in temp_path.iterdir() if path.is_file())
        if len(objects) != len(members):
            raise ValueError(
                f"could not extract every member from Linux iSH archive {archive}: "
                f"listed {len(members)}, extracted {len(objects)}"
            )

        repacked = temp_path / archive.name
        subprocess.run(
            [libtool, "-static", "-o", str(repacked), *(str(path) for path in objects)],
            check=True,
            capture_output=True,
            text=True,
        )
        if not repacked.is_file() or repacked.stat().st_size == 0:
            raise ValueError(f"Apple libtool did not produce a valid archive: {archive}")
        os.replace(repacked, archive)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} MESON_BUILD_DIR", file=sys.stderr)
        return 2

    build_dir = Path(sys.argv[1])
    llvm_ar = shutil.which("llvm-ar")
    libtool = shutil.which("libtool")
    if not llvm_ar or not libtool:
        print("repack-ish-meson-archives.py: requires llvm-ar and Apple's libtool", file=sys.stderr)
        return 2

    try:
        for relative_path in ARCHIVES:
            archive = build_dir / relative_path
            if not archive.is_file():
                raise ValueError(f"missing Linux iSH archive: {archive}")
            repack_archive(archive, llvm_ar, libtool)
            print(f"Repacked {archive} using Apple's static-library format")
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"repack-ish-meson-archives.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
