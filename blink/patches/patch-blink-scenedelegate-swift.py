#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-scenedelegate-swift'
TARGET = 'Blink/SceneDelegate.swift'
REPLACEMENTS = (
    (
        36,
        (
            '\n'
            'import RevenueCat\n'
            '\n'
            'let Blink15BundleID = "sh.blink.blinkshell"\n'
            '\n'
            'class ExternalWindow: UIWindow {\n'
            '  var shadowWindow: UIWindow? = nil\n'
        ),
        (
            '\n'
            'import RevenueCat\n'
            '\n'
            'let Blink15BundleID = "com.hermeslink.app"\n'
            '\n'
            'class ExternalWindow: UIWindow {\n'
            '  var shadowWindow: UIWindow? = nil\n'
        ),
    ),
    (
        173,
        (
            '    willConnectTo session: UISceneSession,\n'
            '    options connectionOptions: UIScene.ConnectionOptions)\n'
            '  {\n'
            '    _ = KBTracker.shared\n'
            '\n'
            '    guard let windowScene = scene as? UIWindowScene else {\n'
        ),
        (
            '    willConnectTo session: UISceneSession,\n'
            '    options connectionOptions: UIScene.ConnectionOptions)\n'
            '  {\n'
            '    HermesLinkAppendLog("scene willConnectTo")\n'
            '    _ = KBTracker.shared\n'
            '\n'
            '    guard let windowScene = scene as? UIWindowScene else {\n'
        ),
    ),
    (
        239,
        (
            '    window.rootViewController = _spCtrl\n'
            '    window.isHidden = false\n'
            '\n'
            '    // Await until scene and streams are ready\n'
            '    // NOTE We could also store the contexts and use them later.\n'
            '    DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {\n'
        ),
        (
            '    window.rootViewController = _spCtrl\n'
            '    window.isHidden = false\n'
            '\n'
            '    if session.role == .windowApplication {\n'
            '      DispatchQueue.main.async { [weak self] in\n'
            '        if UserDefaults.standard.object(forKey: "HermesLinkAutoStartWebUI") == nil ||\n'
            '           UserDefaults.standard.bool(forKey: "HermesLinkAutoStartWebUI") {\n'
            '          self?._spCtrl.startHermesWebUI()\n'
            '        }\n'
            '      }\n'
            '    }\n'
            '\n'
            '    // Await until scene and streams are ready\n'
            '    // NOTE We could also store the contexts and use them later.\n'
            '    DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-scenedelegate-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
