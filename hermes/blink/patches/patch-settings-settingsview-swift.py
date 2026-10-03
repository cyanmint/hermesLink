#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-settings-settingsview-swift'
TARGET = 'Settings/SettingsView.swift'
REPLACEMENTS = (
    (
        42,
        (
            '  @State private var _iCloudSyncOn = BKUserConfigurationManager.userSettingsValue(forKey: BKUserConfigiCloud)\n'
            '  @State private var _autoLockOn = BKUserConfigurationManager.userSettingsValue(forKey: BKUserConfigAutoLock)\n'
            '  @State private var _defaultUser = BLKDefaults.defaultUserName() ?? ""\n'
            '  @StateObject private var _entitlements: EntitlementsManager = .shared\n'
            '  @StateObject private var _model = PurchasesUserModel.shared\n'
            '  @State private var _displayBlinkClassicToPlus = false\n'
        ),
        (
            '  @State private var _iCloudSyncOn = BKUserConfigurationManager.userSettingsValue(forKey: BKUserConfigiCloud)\n'
            '  @State private var _autoLockOn = BKUserConfigurationManager.userSettingsValue(forKey: BKUserConfigAutoLock)\n'
            '  @State private var _defaultUser = BLKDefaults.defaultUserName() ?? ""\n'
            '  @State private var _autoStartHermesWebUI = UserDefaults.standard.object(forKey: "HermesLinkAutoStartWebUI") == nil || UserDefaults.standard.bool(forKey: "HermesLinkAutoStartWebUI")\n'
            '  @State private var _openWebUIInForeground = UserDefaults.standard.object(forKey: "HermesLinkOpenWebUIInForeground") == nil || UserDefaults.standard.bool(forKey: "HermesLinkOpenWebUIInForeground")\n'
            '  @State private var _diagnosticsOn = HermesLinkDiagnosticsEnabled()\n'
            '\n'
            '  @StateObject private var _entitlements: EntitlementsManager = .shared\n'
            '  @StateObject private var _model = PurchasesUserModel.shared\n'
            '  @State private var _displayBlinkClassicToPlus = false\n'
        ),
    ),
    (
        150,
        (
            '#endif\n'
            '      }\n'
            '\n'
            '      Section("Configuration") {\n'
            '        Row {\n'
            '          Label("Bookmarks", systemImage: "bookmark")\n'
        ),
        (
            '#endif\n'
            '      }\n'
            '\n'
            '      Section("HermesLink") {\n'
            '        Toggle("Start WebUI when opening", isOn: $_autoStartHermesWebUI)\n'
            '          .onChange(of: _autoStartHermesWebUI) { enabled in\n'
            '            UserDefaults.standard.set(enabled, forKey: "HermesLinkAutoStartWebUI")\n'
            '          }\n'
            '        Toggle("Open WebUI in foreground", isOn: $_openWebUIInForeground)\n'
            '          .onChange(of: _openWebUIInForeground) { enabled in\n'
            '            UserDefaults.standard.set(enabled, forKey: "HermesLinkOpenWebUIInForeground")\n'
            '          }\n'
            '        Toggle("App, Term and WebUI logs", isOn: $_diagnosticsOn)\n'
            '          .onChange(of: _diagnosticsOn) { enabled in\n'
            '            HermesLinkSetDiagnosticsEnabled(enabled)\n'
            '          }\n'
            '        Text("Diagnostics are saved to Documents/hermeslink.log.")\n'
            '          .font(.footnote)\n'
            '          .foregroundColor(.secondary)\n'
            '        Text("Three-finger swipe up opens settings. Three-finger swipe down opens the WebUI at 127.0.0.1:8787.")\n'
            '          .font(.footnote)\n'
            '          .foregroundColor(.secondary)\n'
            '      }\n'
            '\n'
            '      Section("iSH") {\n'
            '        Row {\n'
            '          Label("Rootfs Profiles", systemImage: "terminal")\n'
            '        } details: {\n'
            '          ISHRootfsSettingsView()\n'
            '        }\n'
            '      }\n'
            '\n'
            '      Section("Configuration") {\n'
            '        Row {\n'
            '          Label("Bookmarks", systemImage: "bookmark")\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-settings-settingsview-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
