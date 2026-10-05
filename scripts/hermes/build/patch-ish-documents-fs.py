#!/usr/bin/env python3
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Add the direct host-backed Documents filesystem to the pinned iSH Linux build."""

from __future__ import annotations

import sys
from pathlib import Path


MESON_KERNEL_SOURCES = """    kernel_src = [
        'linux/main.c',
        'linux/fakefs.c',
    ]
"""
MESON_KERNEL_SOURCES_PATCHED = MESON_KERNEL_SOURCES + """
    documentsfs_module = static_library('documentsfs_module',
        'linux/documentsfs.c',
        dependencies: [linux_headers, sqlite3])
"""
MESON_LINK_WHOLE = "declare_dependency(link_whole: [modules, user_modules])"
MESON_LINK_WHOLE_PATCHED = (
    "declare_dependency(link_whole: [modules, user_modules, documentsfs_module])"
)


def patch(source_root: Path, documents_fs_source: Path) -> None:
    meson_path = source_root / "meson.build"
    destination = source_root / "linux" / "documentsfs.c"
    meson = meson_path.read_text(encoding="utf-8")
    source = documents_fs_source.read_text(encoding="utf-8")

    if MESON_KERNEL_SOURCES_PATCHED not in meson:
        if meson.count(MESON_KERNEL_SOURCES) != 1:
            raise ValueError("unexpected pinned iSH Linux Meson kernel source list")
        meson = meson.replace(
            MESON_KERNEL_SOURCES, MESON_KERNEL_SOURCES_PATCHED, 1
        )
    if MESON_LINK_WHOLE_PATCHED not in meson:
        if meson.count(MESON_LINK_WHOLE) != 1:
            raise ValueError("unexpected pinned iSH Linux Meson link declaration")
        meson = meson.replace(MESON_LINK_WHOLE, MESON_LINK_WHOLE_PATCHED, 1)
    if destination.exists():
        if destination.read_text(encoding="utf-8") != source:
            raise ValueError(f"refusing to replace an existing file: {destination}")
    else:
        destination.write_text(source, encoding="utf-8")
    meson_path.write_text(meson, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: patch-ish-documents-fs.py <pinned-ish-source-root> <documentsfs.c>",
              file=sys.stderr)
        return 2
    try:
        patch(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError) as error:
        print(f"patch-ish-documents-fs.py: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
