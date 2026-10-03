#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-settings-viewcontrollers-about-about-html'
TARGET = 'Settings/ViewControllers/About/about.html'
REPLACEMENTS = (
    (
        2,
        (
            '<html>\n'
            '  <head>\n'
            '    <meta charset="utf-8">\n'
            '    <title>About Blink Shell</title>\n'
            '    <link rel="stylesheet" href="css/normalize.css" type="text/css" media="screen" />\n'
            '    <link rel="stylesheet" href="css/skeleton.css" type="text/css" media="screen" />\n'
            '    <link rel="stylesheet" href="css/custom.css" type="text/css" media="screen" />\n'
        ),
        (
            '<html>\n'
            '  <head>\n'
            '    <meta charset="utf-8">\n'
            '    <title>About HermesLink</title>\n'
            '    <link rel="stylesheet" href="css/normalize.css" type="text/css" media="screen" />\n'
            '    <link rel="stylesheet" href="css/skeleton.css" type="text/css" media="screen" />\n'
            '    <link rel="stylesheet" href="css/custom.css" type="text/css" media="screen" />\n'
        ),
    ),
    (
        14,
        (
            '      <div class="container">\n'
            '\t<div class="row">\n'
            '\t  <div class="twelve column">\n'
            '\t    <h4>Copyright © 2019 The Blink Shell Project</h4>\n'
            '\t    <p>Thank you for supporting Blink! Blink Shell is fully Open Source Software. You are welcome to use it, modify it and redistribute it under certain conditions, specified under the terms of the GNU General Public License. In addition, Blink is also subject to certain additional terms under the GNU GPL version 3 section 7.</p>\n'
            '\t  </div>\n'
            '\t</div>\n'
            '      </div>\n'
            '      <div class="container description">\n'
            '\t<div class="row">\n'
            '\t  <div class="twelve columns">\n'
            '\t    <p>Blink Shell makes use of and would like to thank the following open source projects:</p>\n'
            '\t    <ul>\n'
            '\t      <li><a href="https://mosh.mit.edu">Mosh</a> © 2012 Keith Winstein; GPLv3 license with OpenSSL linking exception, OCB patent grant and iOS waiver.\n'
            '\t\t<p>Mosh was written by Keith Winstein, along with Anders Kaseorg, Quentin Smith, Richard Tibbetts, Keegan McAllister, and John Hood.</p>\n'
        ),
        (
            '      <div class="container">\n'
            '\t<div class="row">\n'
            '\t  <div class="twelve column">\n'
            '\t    <h4>HermesLink</h4>\n'
            '\t    <p>HermesLink is the project as a whole. It is distributed under the GNU General Public License, version 3 (GPLv3).</p>\n'
            "\t    <p>HermesLink is built on <strong>Blink</strong>, which is included as a dependency and remains subject to Blink's GPLv3 license and additional terms under GNU GPL version 3 section 7.</p>\n"
            '\t    <p>This project includes the following Hermes components: <strong>Hermes Agent</strong> (MIT license, Copyright © 2025 Nous Research) and <strong>Hermes WebUI</strong> (MIT license, Copyright © 2025 Hermes Web UI Contributors).</p>\n'
            "\t    <p>The HermesLink glue files listed in the project's <strong>AI-GENERATED-FILES.md</strong> notice were created by cyanmint's coding agent. AI-generated content has no copyright holder and is not subject to copyright; these files are provided as non-copyrightable glue code. This notice does not alter the licenses or copyright notices of Blink or other third-party components.</p>\n"
            '\t  </div>\n'
            '\t</div>\n'
            '      </div>\n'
            '      <div class="container description">\n'
            '\t<div class="row">\n'
            '\t  <div class="twelve columns">\n'
            '\t    <p>HermesLink makes use of and would like to thank the following open source projects:</p>\n'
            '\t    <ul>\n'
            '\t      <li><a href="https://mosh.mit.edu">Mosh</a> © 2012 Keith Winstein; GPLv3 license with OpenSSL linking exception, OCB patent grant and iOS waiver.\n'
            '\t\t<p>Mosh was written by Keith Winstein, along with Anders Kaseorg, Quentin Smith, Richard Tibbetts, Keegan McAllister, and John Hood.</p>\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-settings-viewcontrollers-about-about-html.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
