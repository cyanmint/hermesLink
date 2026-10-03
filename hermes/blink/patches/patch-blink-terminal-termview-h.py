#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-terminal-termview-h'
TARGET = 'Blink/Terminal/TermView.h'
REPLACEMENTS = (
    (
        35,
        (
            '\n'
            '@class TermView;\n'
            '@class TermDevice;\n'
            '@class TermInput;\n'
            '@class TermUIState;\n'
            '@class LayoutConstraintManager;\n'
            '\n'
        ),
        (
            '\n'
            '@class TermView;\n'
            '@class TermDevice;\n'
            '@protocol TermInput;\n'
            '@class TermUIState;\n'
            '@class LayoutConstraintManager;\n'
            '\n'
        ),
    ),
    (
        46,
        (
            '\n'
            '@property BOOL rawMode;\n'
            '\n'
            '- (void)viewIsReady;\n'
            '- (void)viewFontSizeChanged:(NSInteger)size;\n'
            '- (void)viewWinSizeChanged:(struct winsize)win;\n'
        ),
        (
            '\n'
            '@property BOOL rawMode;\n'
            '\n'
            '- (void)attachInput:(UIView<TermInput> *)termInput;\n'
            '- (void)focus;\n'
            '\n'
            '- (void)viewIsReady;\n'
            '- (void)viewFontSizeChanged:(NSInteger)size;\n'
            '- (void)viewWinSizeChanged:(struct winsize)win;\n'
        ),
    ),
    (
        120,
        (
            '- (void)displayInput:(NSString *)input;\n'
            '- (void)apiResponse:(NSString *)name response:(NSString *)response;\n'
            '- (void)addBrowserWebView:(NSURL *)url agent: (NSString *)agent injectUIO: (BOOL) injectUIO;\n'
            '\n'
            '- (void)modifySideOfSelection;\n'
            '- (void)modifySelectionInDirection:(NSString *)direction granularity:(NSString *)granularity;\n'
        ),
        (
            '- (void)displayInput:(NSString *)input;\n'
            '- (void)apiResponse:(NSString *)name response:(NSString *)response;\n'
            '- (void)addBrowserWebView:(NSURL *)url agent: (NSString *)agent injectUIO: (BOOL) injectUIO;\n'
            '- (void)showBrowserWebView:(NSURL *)url;\n'
            '- (void)moveSharedBrowserWebViewIfPresent;\n'
            '\n'
            '- (void)modifySideOfSelection;\n'
            '- (void)modifySelectionInDirection:(NSString *)direction granularity:(NSString *)granularity;\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-terminal-termview-h.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
