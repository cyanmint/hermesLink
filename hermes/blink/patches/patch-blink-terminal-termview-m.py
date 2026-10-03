#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-terminal-termview-m'
TARGET = 'Blink/Terminal/TermView.m'
REPLACEMENTS = (
    (
        57,
        (
            '@interface TermView () <WKScriptMessageHandler, WKUIDelegate, WKNavigationDelegate, UIGestureRecognizerDelegate, UIEditMenuInteractionDelegate>\n'
            '@end\n'
            '\n'
            '@implementation TermView {\n'
            '  WKWebViewGesturesInteraction *_gestureInteraction;\n'
            '  \n'
        ),
        (
            '@interface TermView () <WKScriptMessageHandler, WKUIDelegate, WKNavigationDelegate, UIGestureRecognizerDelegate, UIEditMenuInteractionDelegate>\n'
            '@end\n'
            '\n'
            'static VSCodeInput *SharedBrowserView;\n'
            '\n'
            '@implementation TermView {\n'
            '  WKWebViewGesturesInteraction *_gestureInteraction;\n'
            '  \n'
        ),
    ),
    (
        220,
        (
            '\n'
            '- (void)addBrowserWebView:(NSURL *)url agent: (NSString *)agent injectUIO: (BOOL) injectUIO\n'
            '{\n'
            '  WKWebViewConfiguration *configuration = [[WKWebViewConfiguration alloc] init];\n'
            '  if (@available(iOS 18.0, *)) {\n'
            '    configuration.writingToolsBehavior = UIWritingToolsBehaviorNone;\n'
        ),
        (
            '\n'
            '- (void)addBrowserWebView:(NSURL *)url agent: (NSString *)agent injectUIO: (BOOL) injectUIO\n'
            '{\n'
            '  if (SharedBrowserView) {\n'
            '    _browserView = SharedBrowserView;\n'
            '    [_browserView removeFromSuperview];\n'
            '    [self addSubview:_browserView];\n'
            '    _browserView.UIDelegate = self;\n'
            '    _browserView.navigationDelegate = self;\n'
            '    _browserView.translatesAutoresizingMaskIntoConstraints = NO;\n'
            '    [NSLayoutConstraint activateConstraints:@[\n'
            '      [_browserView.topAnchor constraintEqualToAnchor:_webView.topAnchor],\n'
            '      [_browserView.leadingAnchor constraintEqualToAnchor:_webView.leadingAnchor],\n'
            '      [_browserView.trailingAnchor constraintEqualToAnchor:_webView.trailingAnchor],\n'
            '      [_browserView.bottomAnchor constraintEqualToAnchor:_webView.bottomAnchor]\n'
            '    ]];\n'
            '    [_browserView loadRequest:[NSURLRequest requestWithURL:url]];\n'
            '    return;\n'
            '  }\n'
            '  WKWebViewConfiguration *configuration = [[WKWebViewConfiguration alloc] init];\n'
            '  if (@available(iOS 18.0, *)) {\n'
            '    configuration.writingToolsBehavior = UIWritingToolsBehaviorNone;\n'
        ),
    ),
    (
        241,
        (
            '\n'
            '\n'
            '  _browserView = [[VSCodeInput alloc] initWithFrame:CGRectZero configuration:configuration];\n'
            '  _browserView.customUserAgent =\n'
            '//  [@"Mozilla/5.0 (Linux; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15 " stringByAppendingString:agent];\n'
            '  [@"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15 " stringByAppendingString:agent];\n'
        ),
        (
            '\n'
            '\n'
            '  _browserView = [[VSCodeInput alloc] initWithFrame:CGRectZero configuration:configuration];\n'
            '  SharedBrowserView = _browserView;\n'
            '  _browserView.customUserAgent =\n'
            '//  [@"Mozilla/5.0 (Linux; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15 " stringByAppendingString:agent];\n'
            '  [@"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15 " stringByAppendingString:agent];\n'
        ),
    ),
    (
        267,
        (
            '  [_browserView loadRequest:request];\n'
            '}\n'
            '\n'
            '- (void)webView:(WKWebView *)webView decidePolicyForNavigationAction:(WKNavigationAction *)navigationAction decisionHandler:(void (^)(WKNavigationActionPolicy))decisionHandler {\n'
            '  decisionHandler(WKNavigationActionPolicyAllow);\n'
            '}\n'
        ),
        (
            '  [_browserView loadRequest:request];\n'
            '}\n'
            '\n'
            '- (void)showBrowserWebView:(NSURL *)url\n'
            '{\n'
            '  [self addBrowserWebView:url agent:@"" injectUIO:NO];\n'
            '  [_device attachInput:_browserView];\n'
            '  [_browserView becomeFirstResponder];\n'
            '}\n'
            '\n'
            '- (void)moveSharedBrowserWebViewIfPresent\n'
            '{\n'
            '  if (SharedBrowserView && SharedBrowserView.superview != self) {\n'
            '    [self addBrowserWebView:SharedBrowserView.URL agent:@"" injectUIO:NO];\n'
            '  }\n'
            '}\n'
            '\n'
            '- (void)webView:(WKWebView *)webView decidePolicyForNavigationAction:(WKNavigationAction *)navigationAction decisionHandler:(void (^)(WKNavigationActionPolicy))decisionHandler {\n'
            '  decisionHandler(WKNavigationActionPolicyAllow);\n'
            '}\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-terminal-termview-m.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
