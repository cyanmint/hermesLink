#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-whatsnew-whatsnewinfo-swift'
TARGET = 'Blink/WhatsNew/WhatsNewInfo.swift'
REPLACEMENTS = (
    (
        47,
        (
            '  }\n'
            '  static private var firstUsagePrompt: String {\n'
            '    """\n'
            '\\u{1B}[30;48;5;45m Type \\u{1B}[0m\\u{1B}[38;5;45m\ue0b0\\u{1B}[0m\n'
            'ssh, mosh - Connect to remote\n'
            'code - Code session\n'
            'build - Build dev environments\n'
        ),
        (
            '  }\n'
            '  static private var firstUsagePrompt: String {\n'
            '    """\n'
            '\\u{1B}[30;48;5;45m Type \\u{1B}[0m \\u{1B}[38;5;45m\ue0b0\\u{1B}[0m\n'
            'Run `hermes model` to sign in to your model provider.\n'
            'Three-finger swipe up - Open settings\n'
            'Three-finger swipe down - Open the WebUI at 127.0.0.1:8787\n'
            'ssh, mosh - Connect to remote\n'
            'code - Code session\n'
            'build - Build dev environments\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-whatsnew-whatsnewinfo-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
