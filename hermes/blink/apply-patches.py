#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply-patches.py <blink-source-root>")

    source_root = Path(sys.argv[1]).resolve()
    patch_dir = Path(__file__).resolve().parent / "patches"
    scripts = sorted(patch_dir.glob("patch-*.py"))
    if not scripts:
        raise SystemExit(f"no Blink patch scripts found in {patch_dir}")

    patch_environment = os.environ.copy()
    patch_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    for script in scripts:
        subprocess.run(
            [sys.executable, str(script), str(source_root)],
            check=True,
            env=patch_environment,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
