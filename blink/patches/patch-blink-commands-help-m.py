#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-commands-help-m'
TARGET = 'Blink/Commands/help.m'
REPLACEMENTS = (
    (
        64,
        (
            '    @"  mosh: mosh client.",\n'
            '    @"  ssh: ssh client.",\n'
            '    @"  config: Setup ssh keys, hosts, keyboard, etc.",\n'
            '    @"  code: code editor. (don\'t forget install blink-fs extension)",\n'
            '    @"  help: Prints this.",\n'
            '    @"  whatsnew: Discover new features.",\n'
            '    @"  exit: Close this shell.",\n'
            '    @"",\n'
            '    @"Gestures:",\n'
            '    @"  ✌️ tap -> New Terminal.  ",\n'
            '    @"  👆 tap -> Mouse click.  ",\n'
            '    @"  👆 swipe left/right -> Switch Terminals.  ",\n'
        ),
        (
            '    @"  mosh: mosh client.",\n'
            '    @"  ssh: ssh client.",\n'
            '    @"  config: Setup ssh keys, hosts, keyboard, etc.",\n'
            '    @"  hermes model: Sign in to your model provider.",\n'
            '    @"  hermes webui: Start the Hermes WebUI at 127.0.0.1:8787.",\n'
            '    @"  ish <command>: Run a command in the persistent Alpine Linux guest.",\n'
            '    @"  code: code editor. (don\'t forget install blink-fs extension)",\n'
            '    @"  help: Prints this.",\n'
            '    @"  whatsnew: Discover new features.",\n'
            '    @"  exit: Close this shell.",\n'
            '    @"",\n'
            '    @"Gestures:",\n'
            '    @"  Three-finger swipe up -> Open settings.",\n'
            '    @"  Three-finger swipe down -> Open the Hermes WebUI.",\n'
            '    @"  ✌️ tap -> New Terminal.  ",\n'
            '    @"  👆 tap -> Mouse click.  ",\n'
            '    @"  👆 swipe left/right -> Switch Terminals.  ",\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-commands-help-m.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
