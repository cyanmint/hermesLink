#!/usr/bin/env python3
"""Teach the pinned legacy xcbuild resolver to skip SwiftPM package references."""

from __future__ import annotations

import sys
from pathlib import Path


def patch_dependency_resolver(xcbuild_root: Path) -> None:
    source = (
        xcbuild_root
        / "Libraries"
        / "pbxbuild"
        / "Sources"
        / "Build"
        / "DependencyResolver.cpp"
    )
    contents = source.read_text(encoding="utf-8")
    original = (
        "        for (pbxproj::PBX::BuildFile::shared_ptr const &file : buildPhase->files()) {\n"
        "            switch (file->fileRef()->type()) {"
    )
    patched = (
        "        for (pbxproj::PBX::BuildFile::shared_ptr const &file : buildPhase->files()) {\n"
        "            if (file == nullptr || file->fileRef() == nullptr) {\n"
        "                continue;\n"
        "            }\n"
        "            switch (file->fileRef()->type()) {"
    )

    if patched in contents:
        return
    if contents.count(original) != 1:
        raise SystemExit(f"expected one DependencyResolver patch anchor in {source}")
    source.write_text(contents.replace(original, patched, 1), encoding="utf-8", newline="\n")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} XCBUILD_SOURCE_ROOT")
    patch_dependency_resolver(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
