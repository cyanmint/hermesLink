#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blinkconfig-blinkpaths-m'
TARGET = 'BlinkConfig/BlinkPaths.m'
REPLACEMENTS = (
    (
        64,
        (
            '  return __documentsPath;\n'
            '}\n'
            '\n'
            '+ (NSString *)groupContainerPath {\n'
            '  if (__groupContainerPath == nil) {\n'
            '\n'
        ),
        (
            '  return __documentsPath;\n'
            '}\n'
            '\n'
            '+ (NSString *)hermesHomePath\n'
            '{\n'
            '  NSString *path = [[self documentsPath] stringByAppendingPathComponent:@"HermesHome"];\n'
            '  [self _ensureFolderAtPath:path];\n'
            '  return path;\n'
            '}\n'
            '\n'
            '+ (NSString *)groupContainerPath {\n'
            '  if (__groupContainerPath == nil) {\n'
            '\n'
        ),
    ),
    (
        71,
        (
            '\n'
            '    NSFileManager *fm = [NSFileManager defaultManager];\n'
            '    NSString *path = [fm containerURLForSecurityApplicationGroupIdentifier:groupID].path;\n'
            '    __groupContainerPath = path;\n'
            '  }\n'
            '  return __groupContainerPath;\n'
        ),
        (
            '\n'
            '    NSFileManager *fm = [NSFileManager defaultManager];\n'
            '    NSString *path = [fm containerURLForSecurityApplicationGroupIdentifier:groupID].path;\n'
            '    if (path.length == 0) {\n'
            '      // TrollStore/ad-hoc installs may not receive a provisioned App Group.\n'
            '      // Never pass nil to URL(fileURLWithPath:): Migrator runs before the\n'
            '      // first scene and would trap during launch. Use an app-local durable\n'
            '      // directory until a real App Group becomes available.\n'
            '      NSString *applicationSupport = [NSSearchPathForDirectoriesInDomains(\n'
            '        NSApplicationSupportDirectory, NSUserDomainMask, YES) firstObject];\n'
            '      path = [applicationSupport stringByAppendingPathComponent:@"HermesLink"];\n'
            '      [self _ensureFolderAtPath:path];\n'
            '      NSLog(@"App Group %@ unavailable; using app-local container %@", groupID, path);\n'
            '    }\n'
            '    __groupContainerPath = path;\n'
            '  }\n'
            '  return __groupContainerPath;\n'
        ),
    ),
    (
        102,
        (
            '\n'
            '+ (void)_linkAtPath:(NSString *)path destinationPath:(NSString *)destinationPath {\n'
            '  NSFileManager *fm = [NSFileManager defaultManager];\n'
            '  \n'
            "  // Don't use fileExists as that would traverse the symlink.\n"
            '  if ([fm attributesOfItemAtPath:path error:nil]) {\n'
        ),
        (
            '\n'
            '+ (void)_linkAtPath:(NSString *)path destinationPath:(NSString *)destinationPath {\n'
            '  NSFileManager *fm = [NSFileManager defaultManager];\n'
            '\n'
            '  if (path.length == 0 || destinationPath.length == 0) {\n'
            '    NSLog(@"Skipping link with unavailable path (source=%@, destination=%@)", path, destinationPath);\n'
            '    return;\n'
            '  }\n'
            '  \n'
            "  // Don't use fileExists as that would traverse the symlink.\n"
            '  if ([fm attributesOfItemAtPath:path error:nil]) {\n'
        ),
    ),
    (
        155,
        (
            '+ (void)_ensureFolderAtPath:(NSString *)path {\n'
            '  BOOL isDir = NO;\n'
        ),
        (
            '+ (void)_ensureFolderAtPath:(NSString *)path {\n'
            '  if (path.length == 0) {\n'
            '    NSLog(@"Skipping folder creation for unavailable path");\n'
            '    return;\n'
            '  }\n'
            '  BOOL isDir = NO;\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blinkconfig-blinkpaths-m.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
