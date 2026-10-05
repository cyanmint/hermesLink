#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-terminal-termcontroller-swift'
TARGET = 'Blink/Terminal/TermController.swift'
REPLACEMENTS = (
    (
        75,
        (
            '      else {\n'
            '        return\n'
            '      }\n'
            '      controlledView.frame = frame\n'
            '    }\n'
            '\n'
            '    placeControlledView()\n'
        ),
        (
            '      else {\n'
            '        return\n'
            '      }\n'
            '      guard let proxy = self else { return }\n'
            '      if controlledView.superview === proxy {\n'
            '        controlledView.frame = proxy.bounds\n'
            '      } else if controlledView.superview === parent {\n'
            '        controlledView.frame = frame\n'
            '      }\n'
            '    }\n'
            '\n'
            '    placeControlledView()\n'
        ),
    ),
    (
        89,
        (
            '    else {\n'
            '      return\n'
            '    }\n'
            '    controlledView.frame = parent.frame\n'
            '  }\n'
            '\n'
            '  func removeControlledView() {\n'
        ),
        (
            '    else {\n'
            '      return\n'
            '    }\n'
            '    if controlledView.superview === self {\n'
            '      controlledView.frame = bounds\n'
            '    } else if controlledView.superview === parent {\n'
            '      // The controlled terminal is temporarily reparented beside this proxy.\n'
            "      // Use the proxy's frame in that container's coordinate space; using\n"
            "      // parent.frame here uses the container's coordinates twice and can\n"
            '      // collapse the terminal to the two-row startup height.\n'
            '      controlledView.frame = frame\n'
            '    }\n'
            '  }\n'
            '\n'
            '  func removeControlledView() {\n'
        ),
    ),
    (
        193,
        (
            '\n'
            '  @objc var termView: TermView { _termView }\n'
            '\n'
            '  private var _sessionPayload: TermSessionPayload? = nil\n'
            '  private var _session: Session? { _sessionPayload?.session }\n'
            '\n'
        ),
        (
            '\n'
            '  @objc var termView: TermView { _termView }\n'
            '\n'
            '  @objc func enqueueCommand(_ command: String) {\n'
            '    (_session as? MCPSession)?.enqueueCommand(command, skipHistoryRecord: true)\n'
            '  }\n'
            '\n'
            '  private var _sessionPayload: TermSessionPayload? = nil\n'
            '  private var _session: Session? { _sessionPayload?.session }\n'
            '\n'
        ),
    ),
    (
        237,
        (
            '  }\n'
            '\n'
            '  public override func loadView() {\n'
            '    super.loadView()\n'
            '    _termDevice.delegate = self\n'
            '    _termDevice.attachView(_termView)\n'
        ),
        (
            '  }\n'
            '\n'
            '  public override func loadView() {\n'
            '    HermesLinkAppendLog("TermController loadView")\n'
            '    super.loadView()\n'
            '    _termDevice.delegate = self\n'
            '    _termDevice.attachView(_termView)\n'
        ),
    ),
    (
        248,
        (
            '  }\n'
            '\n'
            '  public override func viewDidLoad() {\n'
            '    super.viewDidLoad()\n'
            '    viewIsLoaded = true\n'
            '\n'
        ),
        (
            '  }\n'
            '\n'
            '  public override func viewDidLoad() {\n'
            '    HermesLinkAppendLog("TermController viewDidLoad")\n'
            '    super.viewDidLoad()\n'
            '    viewIsLoaded = true\n'
            '\n'
        ),
    ),
    (
        270,
        (
            '\n'
            '  public override func viewDidLayoutSubviews() {\n'
            '    super.viewDidLayoutSubviews()\n'
            '    _termView.termUIState.viewSize = view.bounds.size\n'
            '  }\n'
            '\n'
            '  @objc public func terminate() {\n'
        ),
        (
            '\n'
            '  public override func viewDidLayoutSubviews() {\n'
            '    super.viewDidLayoutSubviews()\n'
            '    let newSize = view.bounds.size\n'
            '    let didChangeSize = _termView.termUIState.viewSize != newSize\n'
            '    _termView.termUIState.viewSize = newSize\n'
            '\n'
            "    // Session startup can precede the proxy view's final bounds. hterm then\n"
            '    // reports a temporary size (often two rows) and keeps using it until the\n'
            '    // next resize. Re-send SIGWINCH after every real bounds change.\n'
            '    if didChangeSize {\n'
            '      _session?.sigwinch()\n'
            '    }\n'
            '  }\n'
            '\n'
            '  @objc public func terminate() {\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-terminal-termcontroller-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
