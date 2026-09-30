#!/usr/bin/env python3
"""Ensure native TLS/hash extensions are built into the embedded iOS runtime."""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_STATIC_MODULES = (
    ("_posixsubprocess", "_posixsubprocess.c"),
    (
        "_blake2",
        "_blake2/blake2module.c _blake2/blake2b_impl.c _blake2/blake2s_impl.c",
    ),
    ("_ssl", "_ssl.c"),
    ("_hashlib", "_hashopenssl.c"),
)


def ensure_required_static_modules(lines: list[str]) -> list[str]:
    """Append TLS/hash extensions disabled by CPython's cross-build probes."""
    result = list(lines)
    active_names = set()
    for line in result:
        active = line.split("#", 1)[0].strip()
        if active and not active.startswith("*"):
            active_names.add(active.split()[0])
    for name, source in REQUIRED_STATIC_MODULES:
        if name not in active_names:
            result.append(f"{name} {source}")
            active_names.add(name)
    return result


def module_object_paths(lines: list[str]) -> list[str]:
    """Return object paths for C sources enabled in a CPython Setup file."""
    objects = set()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("*"):
            continue
        for token in line.split()[1:]:
            if token.endswith(".c"):
                source_path = token[2:] if token.startswith("$(srcdir)/") else token
                objects.add("Modules/" + source_path[:-2] + ".o")
    return sorted(objects)


def configure_setup_file(path: Path) -> list[str]:
    lines = ensure_required_static_modules(path.read_text(encoding="utf-8").splitlines())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return [name for name, _source in REQUIRED_STATIC_MODULES]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setup_file", type=Path)
    args = parser.parse_args()
    names = configure_setup_file(args.setup_file)
    print("Enabled required native modules: " + ", ".join(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
