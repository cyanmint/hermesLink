#!/usr/bin/env python3
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Prevent Xcode host libraries from rerunning the Linux Meson build."""

from __future__ import annotations

import re
import sys
from pathlib import Path


MESON_TARGET_ID = "BBECF3AF269136E100DEC937"
HOST_LIBRARY_DEPENDENCIES = {
    "libiSHLinux": "BBECF3BE2691417C00DEC937",
    "libiSHLinuxUser": "BBBDDF812CE00F6A0071F1F3",
}


def remove_meson_dependency(project: str, target: str, dependency_id: str) -> str:
    marker = f"/* {target} */ = {{"
    target_start = project.find(marker)
    if target_start < 0:
        raise ValueError(f"missing pinned iSH Xcode target: {target}")
    target_end = project.find("\n\t\t};", target_start)
    if target_end < 0:
        raise ValueError(f"unterminated pinned iSH Xcode target: {target}")

    block = project[target_start:target_end]
    dependency_pattern = re.compile(
        r"(\n\t\t\tdependencies = \(\n)(.*?)(\n\t\t\t\);)",
        re.DOTALL,
    )
    match = dependency_pattern.search(block)
    expected_entry = f"{dependency_id} /* PBXTargetDependency */,"
    dependency_marker = f"{dependency_id} /* PBXTargetDependency */ = {{"
    dependency_start = project.find(dependency_marker)
    dependency_end = project.find("\n\t\t};", dependency_start)
    if dependency_start < 0 or dependency_end < 0:
        raise ValueError(f"missing pinned dependency for iSH target: {target}")
    dependency_block = project[dependency_start:dependency_end]
    if f"target = {MESON_TARGET_ID} /* liblinux */;" not in dependency_block:
        raise ValueError(f"pinned iSH target {target} no longer depends only on liblinux")

    entries = [] if match is None else [
        line.strip() for line in match.group(2).splitlines() if line.strip()
    ]
    if entries == []:
        return project
    if entries != [expected_entry]:
        raise ValueError(f"unexpected dependency list for pinned iSH target: {target}")

    patched_block = dependency_pattern.sub(
        lambda match: match.group(1) + "\t\t\t);",
        block,
        count=1,
    )
    return project[:target_start] + patched_block + project[target_end:]


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} PROJECT.PBXPROJ", file=sys.stderr)
        return 2

    project_path = Path(sys.argv[1])
    project = project_path.read_text(encoding="utf-8")
    for target, dependency_id in HOST_LIBRARY_DEPENDENCIES.items():
        project = remove_meson_dependency(project, target, dependency_id)
    project_path.write_text(project, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
