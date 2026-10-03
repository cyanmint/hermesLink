#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-complete-swift'
TARGET = 'Blink/Complete.swift'
REPLACEMENTS = (
    (
        97,
        (
            '    if let commands = commandsAsArray() as? [String] {\n'
            '      result.append(contentsOf: commands)\n'
            '    }\n'
            '    result.append(contentsOf: ["mosh", "exit", "ssh-copy-id"])\n'
            '    \n'
            '    let set = Set<String>(result)\n'
            '    result = Array(set)\n'
        ),
        (
            '    if let commands = commandsAsArray() as? [String] {\n'
            '      result.append(contentsOf: commands)\n'
            '    }\n'
            '    result.append(contentsOf: ["hermes", "mosh", "exit", "ssh-copy-id"])\n'
            '    \n'
            '    let set = Set<String>(result)\n'
            '    result = Array(set)\n'
        ),
    ),
    (
        140,
        (
            '      "gzip": "Compression/decompression tool using Lempel-Ziv coding (LZ77)",  // fish\n'
            '      "head": "Display first lines of a file", // fish\n'
            '      "help": "Prints all commands. 🧐 ",\n'
            '      "history": "Use -c option to clear history. 🙈 ",\n'
            '      "host": "DNS lookup utility.", // fish\n'
            '      "less": "Pager.",\n'
        ),
        (
            '      "gzip": "Compression/decompression tool using Lempel-Ziv coding (LZ77)",  // fish\n'
            '      "head": "Display first lines of a file", // fish\n'
            '      "help": "Prints all commands. 🧐 ",\n'
            '      "hermes": "Run the bundled Hermes Agent runtime.",\n'
            '      "history": "Use -c option to clear history. 🙈 ",\n'
            '      "host": "DNS lookup utility.", // fish\n'
            '      "less": "Pager.",\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-complete-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
