#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-spacecontroller-swift'
TARGET = 'Blink/SpaceController.swift'
REPLACEMENTS = (
    (
        36,
        (
            '\n'
            'import MBProgressHUD\n'
            'import SwiftUI\n'
            '\n'
            '\n'
            '// MARK: UIViewController\n'
            'class SpaceController: UIViewController {\n'
            '  \n'
            '  struct UIState: UserActivityCodable {\n'
            '    var keys: [UUID] = []\n'
        ),
        (
            '\n'
            'import MBProgressHUD\n'
            'import SwiftUI\n'
            'import Network\n'
            '\n'
            '\n'
            '// MARK: UIViewController\n'
            'class SpaceController: UIViewController, UIGestureRecognizerDelegate {\n'
            '  \n'
            '  struct UIState: UserActivityCodable {\n'
            '    var keys: [UUID] = []\n'
        ),
    ),
    (
        68,
        (
            '  private var _snippetsVC: SnippetsViewController? = nil\n'
            '  private var _blinkMenu: BlinkMenu? = nil\n'
            '  private var _bottomTapAreaView = UIView()\n'
            '\n'
            '  // Snips Input Mode tracking\n'
            '  private var _isSnipsInputModeActive: Bool = false {\n'
        ),
        (
            '  private var _snippetsVC: SnippetsViewController? = nil\n'
            '  private var _blinkMenu: BlinkMenu? = nil\n'
            '  private var _bottomTapAreaView = UIView()\n'
            '  private var _threeFingerPan: UIPanGestureRecognizer!\n'
            '\n'
            '  // Snips Input Mode tracking\n'
            '  private var _isSnipsInputModeActive: Bool = false {\n'
        ),
    ),
    (
        230,
        (
            '  }\n'
            '  \n'
            '  public override func viewDidLoad() {\n'
            '    super.viewDidLoad()\n'
            '    \n'
            '    _setupAppearance()\n'
        ),
        (
            '  }\n'
            '  \n'
            '  public override func viewDidLoad() {\n'
            '    HermesLinkAppendLog("SpaceController viewDidLoad")\n'
            '    super.viewDidLoad()\n'
            '    \n'
            '    _setupAppearance()\n'
        ),
    ),
    (
        275,
        (
            '    doubleTap.numberOfTapsRequired = 2\n'
            '    doubleTap.numberOfTouchesRequired = 1\n'
            '    _bottomTapAreaView.addGestureRecognizer(doubleTap)\n'
            '    \n'
            '    NotificationCenter.default.addObserver(self, selector: #selector(_geoTrackStateChanged), name: NSNotification.Name.BLGeoTrackStateChange, object: nil)\n'
            '    \n'
        ),
        (
            '    doubleTap.numberOfTapsRequired = 2\n'
            '    doubleTap.numberOfTouchesRequired = 1\n'
            '    _bottomTapAreaView.addGestureRecognizer(doubleTap)\n'
            '\n'
            '    // A pan recognizer is used instead of two UISwipeRecognizers. UISwipe can\n'
            '    // lose the gesture to the terminal/WebView scroll recognizers before it\n'
            '    // decides on a direction, which made the down gesture (and other gestures\n'
            '    // on an interactive terminal) disappear on iPadOS.\n'
            '    _threeFingerPan = UIPanGestureRecognizer(target: self, action: #selector(_handleThreeFingerPan(_:)))\n'
            '    _threeFingerPan.minimumNumberOfTouches = 3\n'
            '    _threeFingerPan.maximumNumberOfTouches = 3\n'
            '    _threeFingerPan.cancelsTouchesInView = false\n'
            '    _threeFingerPan.delegate = self\n'
            '    view.addGestureRecognizer(_threeFingerPan)\n'
            '    \n'
            '    NotificationCenter.default.addObserver(self, selector: #selector(_geoTrackStateChanged), name: NSNotification.Name.BLGeoTrackStateChange, object: nil)\n'
            '    \n'
        ),
    ),
    (
        774,
        (
            '    currentTerm()?.scaleWithPich(pinch)\n'
            '  }\n'
            '  \n'
            '  private func _newShellAction(command: String = "", animated: Bool = true) {\n'
            '    let params = MCPParams()\n'
            '    if !command.isEmpty {\n'
            '      params.initialCommand = command\n'
        ),
        (
            '    currentTerm()?.scaleWithPich(pinch)\n'
            '  }\n'
            '  \n'
            '  func _newShellAction(command: String = "", animated: Bool = true) {\n'
            '    let params = MCPParams()\n'
            '    if !command.isEmpty {\n'
            '      params.initialCommand = command\n'
        ),
    ),
    (
        783,
        (
            '    _createTerminal(userActivity: nil, animated: animated, sessionPayload: payload)\n'
            '  }\n'
            '\n'
            '  @objc func newShellAction() {\n'
            '    _newShellAction()\n'
            '  }\n'
        ),
        (
            '    _createTerminal(userActivity: nil, animated: animated, sessionPayload: payload)\n'
            '  }\n'
            '\n'
            '  private static let hermesWebUIDefaultPort = 8787\n'
            '  private static var hermesWebUIPort: Int?\n'
            '  private static var hermesWebUIStartInFlight = false\n'
            '  private static var hermesWebUIWaiters: [(Int, Bool) -> Void] = []\n'
            '\n'
            '  private static func portIsOccupied(_ port: Int, completion: @escaping (Bool) -> Void) {\n'
            '    guard let endpointPort = NWEndpoint.Port(rawValue: UInt16(port)) else {\n'
            '      completion(true)\n'
            '      return\n'
            '    }\n'
            '\n'
            '    let connection = NWConnection(host: "127.0.0.1", port: endpointPort, using: .tcp)\n'
            '    let lock = NSLock()\n'
            '    var finished = false\n'
            '    let finish: (Bool) -> Void = { occupied in\n'
            '      lock.lock()\n'
            '      guard !finished else {\n'
            '        lock.unlock()\n'
            '        return\n'
            '      }\n'
            '      finished = true\n'
            '      lock.unlock()\n'
            '      connection.cancel()\n'
            '      completion(occupied)\n'
            '    }\n'
            '\n'
            '    connection.stateUpdateHandler = { state in\n'
            '      switch state {\n'
            '      case .ready:\n'
            '        finish(true)\n'
            '      case .failed, .cancelled:\n'
            '        finish(false)\n'
            '      default:\n'
            '        break\n'
            '      }\n'
            '    }\n'
            '    connection.start(queue: DispatchQueue.global(qos: .utility))\n'
            '    DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + 0.5) {\n'
            '      finish(false)\n'
            '    }\n'
            '  }\n'
            '\n'
            '  private static func findHermesWebUIPort(_ port: Int, completion: @escaping (Int, Bool) -> Void) {\n'
            '    // A successful WebUI API response means another HermesLink window (or a\n'
            '    // previously launched app instance) already owns this port.\n'
            '    let url = URL(string: "http://127.0.0.1:\\(port)/api/config")!\n'
            '    URLSession.shared.dataTask(with: url) { _, response, _ in\n'
            '      if response is HTTPURLResponse {\n'
            '        completion(port, false)\n'
            '        return\n'
            '      }\n'
            '\n'
            '      portIsOccupied(port) { occupied in\n'
            '        completion(port, !occupied)\n'
            '      }\n'
            '    }.resume()\n'
            '  }\n'
            '\n'
            '  private func openHermesWebUI(at port: Int, launchServer: Bool) {\n'
            '    HermesLinkAppendLog("opening Hermes WebUI")\n'
            '    let webUITerm = currentTerm()\n'
            '    if launchServer {\n'
            '      // Keep the server in the terminal that owns it. Do not background or\n'
            '      // silence it: this is the diagnostic shell for the WebUI.\n'
            '      webUITerm?.enqueueCommand("hermes webui --host 127.0.0.1 --port \\(port)")\n'
            '    }\n'
            '    if UserDefaults.standard.object(forKey: "HermesLinkOpenWebUIInForeground") == nil ||\n'
            '       UserDefaults.standard.bool(forKey: "HermesLinkOpenWebUIInForeground") {\n'
            '      DispatchQueue.main.asyncAfter(deadline: .now() + (launchServer ? 2.0 : 0.0)) {\n'
            '        guard let webUITerm,\n'
            '              let webURL = URL(string: "http://127.0.0.1:8787") else { return }\n'
            '        webUITerm.termView.showBrowserWebView(webURL)\n'
            '      }\n'
            '    }\n'
            '  }\n'
            '\n'
            '  @objc func startHermesWebUI() {\n'
            '    Self.hermesWebUIWaiters.append { [weak self] port, launchServer in\n'
            '      guard let self else { return }\n'
            '      self.openHermesWebUI(at: port, launchServer: launchServer)\n'
            '    }\n'
            '    guard !Self.hermesWebUIStartInFlight else { return }\n'
            '    Self.hermesWebUIStartInFlight = true\n'
            '\n'
            '    if let port = Self.hermesWebUIPort {\n'
            '      Self.hermesWebUIStartInFlight = false\n'
            '      let waiters = Self.hermesWebUIWaiters\n'
            '      Self.hermesWebUIWaiters.removeAll()\n'
            '      waiters.forEach { $0(port, false) }\n'
            '      return\n'
            '    }\n'
            '\n'
            '    Self.findHermesWebUIPort(Self.hermesWebUIDefaultPort) { port, shouldLaunch in\n'
            '      DispatchQueue.main.async {\n'
            '        Self.hermesWebUIPort = port\n'
            '        Self.hermesWebUIStartInFlight = false\n'
            '        let waiters = Self.hermesWebUIWaiters\n'
            '        Self.hermesWebUIWaiters.removeAll()\n'
            '        waiters.forEach { $0(port, shouldLaunch) }\n'
            '      }\n'
            '    }\n'
            '  }\n'
            '\n'
            '  @objc private func _openHermesWebUI() {\n'
            '    guard let term = currentTerm(),\n'
            '          let url = URL(string: "http://127.0.0.1:8787") else { return }\n'
            '    if Self.hermesWebUIPort == nil {\n'
            '      startHermesWebUI()\n'
            '    }\n'
            '    term.termView.showBrowserWebView(url)\n'
            '  }\n'
            '\n'
            '  @objc func newShellAction() {\n'
            '    _newShellAction()\n'
            '  }\n'
        ),
    ),
    (
        1048,
        (
            '    _interactiveSpaceController()\n'
            '      ._toggleQuickActionActionWith(receiver: self)\n'
            '  }\n'
            '  \n'
            '  @objc func toggleGeoTrack() {\n'
            '    if GeoManager.shared().traking {\n'
            '      GeoManager.shared().stop()\n'
        ),
        (
            '    _interactiveSpaceController()\n'
            '      ._toggleQuickActionActionWith(receiver: self)\n'
            '  }\n'
            '\n'
            '  @objc private func _openTermSettings() {\n'
            '    guard presentedViewController == nil else { return }\n'
            '    showConfigAction()\n'
            '  }\n'
            '\n'
            '  @objc private func _handleThreeFingerPan(_ recognizer: UIPanGestureRecognizer) {\n'
            '    guard recognizer.state == .ended else { return }\n'
            '    let translation = recognizer.translation(in: view)\n'
            '    guard abs(translation.y) > abs(translation.x), abs(translation.y) >= 40 else { return }\n'
            '    if translation.y < 0 {\n'
            '      _openTermSettings()\n'
            '    } else {\n'
            '      _openHermesWebUI()\n'
            '    }\n'
            '  }\n'
            '\n'
            '  func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer,\n'
            '                         shouldRecognizeSimultaneouslyWith otherGestureRecognizer: UIGestureRecognizer) -> Bool {\n'
            '    gestureRecognizer === _threeFingerPan || otherGestureRecognizer === _threeFingerPan\n'
            '  }\n'
            '\n'
            '  @objc func toggleGeoTrack() {\n'
            '    if GeoManager.shared().traking {\n'
            '      GeoManager.shared().stop()\n'
        ),
    ),
    (
        1165,
        (
            '    _viewportsController.setViewControllers([term], direction: direction, animated: animated) { (didComplete) in\n'
            '      term.resumeIfNeeded()\n'
            '      self._currentKey = term.meta.key\n'
            '      self._displayHUD()\n'
            '      self._attachInputToCurrentTerm()\n'
            '      self._spaceControllerAnimating = false\n'
        ),
        (
            '    _viewportsController.setViewControllers([term], direction: direction, animated: animated) { (didComplete) in\n'
            '      term.resumeIfNeeded()\n'
            '      self._currentKey = term.meta.key\n'
            '      term.termView.moveSharedBrowserWebViewIfPresent()\n'
            '      self._displayHUD()\n'
            '      self._attachInputToCurrentTerm()\n'
            '      self._spaceControllerAnimating = false\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-spacecontroller-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
