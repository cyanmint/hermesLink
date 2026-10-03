#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-sessions-sessionparams-swift'
TARGET = 'Sessions/SessionParams.swift'
REPLACEMENTS = (
    (
        125,
        (
            '@objc class MCPParams: NSObject, NSSecureCoding, BKSessionParamsSnapshotting {\n'
            '  @objc var childSessionType: String? = nil\n'
            '  @objc var childSessionParams: BKSessionParams?\n'
            '\n'
            '  /// Command to run when the session bootstraps. Ephemeral — not encoded.\n'
            '  /// Consumed once inside `MCPSession.executeWithArgs:`.\n'
            '  @objc var initialCommand: String? = nil\n'
            '\n'
            '  private enum Key: CodingKey { case childSessionType, childSessionParams }\n'
            '\n'
            '  override init() { super.init() }\n'
            '\n'
        ),
        (
            '@objc class MCPParams: NSObject, NSSecureCoding, BKSessionParamsSnapshotting {\n'
            '  @objc var childSessionType: String? = nil\n'
            '  @objc var childSessionParams: BKSessionParams?\n'
            '  @objc var viewSize: CGSize = .zero\n'
            '  @objc var rows: Int = 0\n'
            '  @objc var cols: Int = 0\n'
            '  @objc var themeName: String? = nil\n'
            '  @objc var fontName: String? = nil\n'
            '  @objc var fontSize: Int = 16\n'
            '  @objc var layoutMode: Int = 0\n'
            '  @objc var boldAsBright: Bool = false\n'
            '  @objc var enableBold: UInt = 0\n'
            '  @objc var layoutLocked: Bool = false\n'
            '  @objc var layoutLockedFrame: CGRect = .zero\n'
            '\n'
            '  /// Command to run when the session bootstraps. Ephemeral — not encoded.\n'
            '  /// Consumed once inside `MCPSession.executeWithArgs:`.\n'
            '  @objc var initialCommand: String? = nil\n'
            '\n'
            '  private enum Key: CodingKey {\n'
            '    case childSessionType, childSessionParams, viewSize, rows, cols, themeName, fontName, fontSize\n'
            '    case layoutMode, boldAsBright, enableBold, layoutLocked, layoutLockedFrame\n'
            '  }\n'
            '\n'
            '  override init() { super.init() }\n'
            '\n'
        ),
    ),
    (
        140,
        (
            '  func encode(with coder: NSCoder) {\n'
            '    coder.bk_encode(childSessionType, for: Key.childSessionType)\n'
            '    coder.bk_encode(childSessionParams, for: Key.childSessionParams)\n'
            '  }\n'
            '\n'
            '  required init?(coder: NSCoder) {\n'
        ),
        (
            '  func encode(with coder: NSCoder) {\n'
            '    coder.bk_encode(childSessionType, for: Key.childSessionType)\n'
            '    coder.bk_encode(childSessionParams, for: Key.childSessionParams)\n'
            '    coder.bk_encode(viewSize, for: Key.viewSize)\n'
            '    coder.bk_encode(rows, for: Key.rows)\n'
            '    coder.bk_encode(cols, for: Key.cols)\n'
            '    coder.bk_encode(themeName, for: Key.themeName)\n'
            '    coder.bk_encode(fontName, for: Key.fontName)\n'
            '    coder.bk_encode(fontSize, for: Key.fontSize)\n'
            '    coder.bk_encode(layoutMode, for: Key.layoutMode)\n'
            '    coder.bk_encode(boldAsBright, for: Key.boldAsBright)\n'
            '    coder.bk_encode(enableBold, for: Key.enableBold)\n'
            '    coder.bk_encode(layoutLocked, for: Key.layoutLocked)\n'
            '    coder.bk_encode(layoutLockedFrame, for: Key.layoutLockedFrame)\n'
            '  }\n'
            '\n'
            '  required init?(coder: NSCoder) {\n'
        ),
    ),
    (
        147,
        (
            '    self.childSessionType = coder.bk_decode(for: Key.childSessionType)\n'
            '    // NOTE: include all known MCP children subclasses here for secure decoding\n'
            '    self.childSessionParams = coder.bk_decode(of: [MoshParams.self], for: Key.childSessionParams)\n'
            '  }\n'
            '\n'
            '  // MARK: - BKSessionParamsSnapshotting (forward)\n'
        ),
        (
            '    self.childSessionType = coder.bk_decode(for: Key.childSessionType)\n'
            '    // NOTE: include all known MCP children subclasses here for secure decoding\n'
            '    self.childSessionParams = coder.bk_decode(of: [MoshParams.self], for: Key.childSessionParams)\n'
            '    self.viewSize = coder.bk_decode(for: Key.viewSize)\n'
            '    self.rows = coder.bk_decode(for: Key.rows)\n'
            '    self.cols = coder.bk_decode(for: Key.cols)\n'
            '    self.themeName = coder.bk_decode(for: Key.themeName)\n'
            '    self.fontName = coder.bk_decode(for: Key.fontName)\n'
            '    self.fontSize = coder.bk_decode(for: Key.fontSize)\n'
            '    self.layoutMode = coder.bk_decode(for: Key.layoutMode)\n'
            '    self.boldAsBright = coder.bk_decode(for: Key.boldAsBright)\n'
            '    self.enableBold = coder.bk_decode(for: Key.enableBold)\n'
            '    self.layoutLocked = coder.bk_decode(for: Key.layoutLocked)\n'
            '    self.layoutLockedFrame = coder.bk_decode(for: Key.layoutLockedFrame)\n'
            '  }\n'
            '\n'
            '  // MARK: - BKSessionParamsSnapshotting (forward)\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-sessions-sessionparams-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
