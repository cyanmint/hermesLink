#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-sessions-mcpsession-m'
TARGET = 'Sessions/MCPSession.m'
REPLACEMENTS = (
    (
        33,
        (
            '#include <string.h>\n'
            '#include <libgen.h>\n'
            '#include <sys/stat.h>\n'
            '#include <dispatch/dispatch.h>\n'
            '\n'
            '#import "MCPSession.h"\n'
        ),
        (
            '#include <string.h>\n'
            '#include <libgen.h>\n'
            '#include <sys/stat.h>\n'
            '#include <unistd.h>\n'
            '#include <dispatch/dispatch.h>\n'
            '\n'
            '#import "MCPSession.h"\n'
        ),
    ),
    (
        88,
        (
            '\n'
            '    NSString *homePath = [BlinkPaths homePath];\n'
            '    ios_setMiniRoot(homePath);\n'
            '    [self updateAllowedPaths];\n'
            '\n'
            '    // We are restoring mosh session if possible first.\n'
        ),
        (
            '\n'
            '    NSString *homePath = [BlinkPaths homePath];\n'
            '    ios_setMiniRoot(homePath);\n'
            '    // Use the real shared Documents directory, not homePath/Documents: the\n'
            '    // latter is a symlink created asynchronously and can become a private\n'
            '    // shadow folder if a session starts before that link is installed.\n'
            '    NSString *documentsPath = [BlinkPaths documentsPath];\n'
            '    NSString *workspacePath = [documentsPath stringByAppendingPathComponent:@"workspace"];\n'
            '    NSString *hermesHomePath = [BlinkPaths hermesHomePath];\n'
            '    [[NSFileManager defaultManager] createDirectoryAtPath:workspacePath\n'
            '                               withIntermediateDirectories:YES\n'
            '                                                attributes:nil\n'
            '                                                 error:nil];\n'
            '    setenv("HERMES_HOME", hermesHomePath.UTF8String, 1);\n'
            '    setenv("HERMES_WEBUI_DEFAULT_WORKSPACE", workspacePath.UTF8String, 1);\n'
            '    setenv("TERMINAL_CWD", workspacePath.UTF8String, 1);\n'
            '    setenv("PWD", workspacePath.UTF8String, 1);\n'
            '    chdir(workspacePath.UTF8String);\n'
            '    [self updateAllowedPaths];\n'
            '\n'
            '    // We are restoring mosh session if possible first.\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-sessions-mcpsession-m.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
