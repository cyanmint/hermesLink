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
            '\t      </li>\n'
            '\t      <li><a href="https://chromium.googlesource.com/apps/libapps/+/HEAD/hterm">HTerm</a> © The Chromium OS Authors; 3-clause BSD license</li>\n'
            '\t      <li>This product includes software developed by the OpenSSL Project for use in the <a href="https://www.openssl.org">OpenSSL Toolkit</a>;\n'
            '\t      <li>This product includes cryptographic software written by Eric Young (eay@cryptsoft.com)"</li>\n'
            '\t      <li><a href="https://www.libssh2.org">Libssh2</a>; 3-clause BSD License.\n'
            '\t\t<p>Copyright (c) 2004-2007 Sara Golemon, Copyright (c) 2005,2006 Mikhail Gusarov, Copyright (c) 2006-2007 The Written Word, Inc., Copyright (c) 2007 Eli Fant, Copyright (c) 2009-2014 Daniel Stenberg, Copyright (C) 2008, 2009 Simon Josefsson.</p>\n'
            '\t      </li>\n'
            '\t      <li><a href="https://github.com/kishikawakatsumi/UICKeyChainStore">UICKeyChainStore</a> © 2011 Kishikawa Katsumi; MIT license</li>\n'
            '\t      <li><a href="https://github.com/jdg/MBProgressHUD">MBProgressHUD</a> © 2011 Matej Bukovinski; MIT license</li>\n'
            '\t      <li><a href="https://github.com/google/protobuf/tree/master/src/google/protobuf">Protobuf</a> © Google Inc.; 3-clause BSD License</li>\n'
            '        <li><a href="https://reactjs.org">React</a> © 2013, Facebook, Inc; MIT license</li>\n'
            '        <li><a href="https://github.com/AmokHuginnsson/replxx">Replxx</a> BSD license\n'
            '          <p>\n'
            '          Copyright (c) 2017-2018, Marcin Konarski (amok at codestation.org);\n'
            '          Copyright (c) 2010, Salvatore Sanfilippo (antirez at gmail dot com);\n'
            '          Copyright (c) 2010, Pieter Noordhuis (pcnoordhuis at gmail dot com);\n'
            '          Markus Kuhn -- 2007-05-26 (Unicode 5.0);\n'
            '          Copyright 2001-2004 Unicode, Inc\n'
            '          </p>\n'
            '        </li>\n'
            '        <li><a href="https://github.com/holzschu/ios_system">ios_system</a> by Nicolas Holzschunch\n'
            '          <p>\n'
            '          awk: OpenSource license;\n'
            '          curl, scp, sftp: MIT/X derivate license;\n'
            '          egrep, fgrep, grep, gzip, gunzip: Simplified BSD License (2-clause BSD license);\n'
            '          cat, chflag, compress, cp, date, echo, env, link, ln, printenv, pwd, sed, tar, uncompress, uptime, Revised BSD License (a.k.a. 3-clause BSD license);\n'
            '          chgrp, chksum, chmod, chown, df, du, groups, id, ls, mkdir, mv, readlink, rm, rmdir, stat, sum, touch, tr, uname, wc, whoami: Original BSD License (4-clause BSD license);\n'
            '          </p>\n'
            '        </li>\n'
            '        <li><a href="https://github.com/holzschu/network_ios">network_ios</a> by Nicolas Holzschunch</li>\n'
            '\t      <li>Source Code Pro Font © 2010, 2012 Adobe Systems Inc.; SIL Open Font License, Version 1.1</li>\n'
            '        <li>DejaVu Sans Mono Font © Roy Y.T. Chen; DejaVu Fonts License, Version 1.0</li>\n'
            '\t      <li>Roboto Mono © Google Inc.; Apache License 2.0</li>\n'
            '\t      <li><a href="http://www.entypo.com">Entypo pictograms</a> by Bruce Daniel - <a href="http://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0.</a></li>\n'
            '\t    </ul>\n'
            '\t  </div>\n'
            '\t</div>\n'
        ),
        (
            '      <div class="container">\n'
            '\t<div class="row">\n'
            '\t  <div class="twelve column">\n'
            '\t    <p>HermesLink is distributed under the <a href="https://www.gnu.org/licenses/gpl-3.0.html">GNU GPL version 3 (GPLv3)</a>.</p>\n'
            '\t  </div>\n'
            '\t</div>\n'
            '      </div>\n'
            '      <div class="container description">\n'
            '\t<div class="row">\n'
            '\t  <div class="twelve columns">\n'
            '\t    <h5>HermesLink components and licenses</h5>\n'
            '\t    <ul>\n'
            '\t      <li><a href="https://github.com/cyanmint/hermesLink">HermesLink glue and bridge code and magical mod patches</a> — AI generated content by the agent of @cyanmint; not applicable to copyright protection.</li>\n'
            '\t      <li><a href="https://github.com/NousResearch/hermes-agent/blob/2246c245f51e03eb6a151d19119009156e84659a/LICENSE">Hermes Agent</a> — MIT License.</li>\n'
            '\t      <li><a href="https://github.com/nesquena/hermes-webui/blob/e36f77389191fe9d81cd3a7416772e2f7b022e19/LICENSE">Hermes WebUI</a> — MIT License.</li>\n'
            '\t      <li><a href="https://github.com/blinksh/blink/blob/a90b4423c8b7a86770c24a7eaa6c13b0a5904b18/COPYING">Blink Shell</a> — <a href="https://www.gnu.org/licenses/gpl-3.0.html">GNU GPL version 3</a> with Blink Additional Terms.</li>\n'
            '\t      <li><a href="https://github.com/holzschu/a-shell/blob/master/LICENSE">a-Shell</a> — BSD 3-Clause License.</li>\n'
            '\t      <li><a href="https://github.com/python/cpython/blob/v3.13.9/LICENSE">CPython</a> — Python Software Foundation License Version 2.</li>\n'
            '\t      <li><a href="https://github.com/ish-app/ish/blob/83348361fe65311f6e87ad2e1cbb0ac38d123f69/LICENSE.md">iSH</a> — GNU GPL version 3, including GPLv2-licensed contributions; see also <a href="https://github.com/ish-app/ish/blob/83348361fe65311f6e87ad2e1cbb0ac38d123f69/LICENSE.IOS">iSH iOS additional terms</a>.</li>\n'
            '\t      <li><a href="https://github.com/yury/ios_system/blob/61f51bed3ec03d2620c6a815e222d945aac976e1/LICENSE">ios_system</a> — BSD 3-Clause License.</li>\n'
            '\t      <li><a href="https://mosh.mit.edu">Mosh</a> — GPLv3 with OpenSSL linking exception, OCB patent grant, and iOS waiver. © 2012 Keith Winstein; written with Anders Kaseorg, Quentin Smith, Richard Tibbetts, Keegan McAllister, and John Hood.</li>\n'
            '\t      <li><a href="https://chromium.googlesource.com/apps/libapps/+/HEAD/hterm">HTerm</a> — 3-clause BSD License; © The Chromium OS Authors.</li>\n'
            '\t      <li><a href="https://www.openssl.org">OpenSSL Toolkit</a> — OpenSSL Project acknowledgment.</li>\n'
            '\t      <li>Eric Young — cryptographic software (eay@cryptsoft.com).</li>\n'
            '\t      <li><a href="https://www.libssh2.org">Libssh2</a> — 3-clause BSD License. Copyright © 2004–2007 Sara Golemon; © 2005–2006 Mikhail Gusarov; © 2006–2007 The Written Word, Inc.; © 2007 Eli Fant; © 2009–2014 Daniel Stenberg; © 2008–2009 Simon Josefsson.</li>\n'
            '\t      <li><a href="https://github.com/kishikawakatsumi/UICKeyChainStore">UICKeyChainStore</a> — MIT License; © 2011 Kishikawa Katsumi.</li>\n'
            '\t      <li><a href="https://github.com/jdg/MBProgressHUD">MBProgressHUD</a> — MIT License; © 2011 Matej Bukovinski.</li>\n'
            '\t      <li><a href="https://github.com/google/protobuf/tree/master/src/google/protobuf">Protobuf</a> — 3-clause BSD License; © Google Inc.</li>\n'
            '\t      <li><a href="https://reactjs.org">React</a> — MIT License; © 2013 Facebook, Inc.</li>\n'
            '\t      <li><a href="https://github.com/AmokHuginnsson/replxx">Replxx</a> — BSD License. Copyright © 2017–2018 Marcin Konarski; © 2010 Salvatore Sanfilippo; © 2010 Pieter Noordhuis; Unicode data © 2001–2004 Unicode, Inc.</li>\n'
            '\t      <li><a href="https://github.com/holzschu/ios_system">ios_system</a> — awk (Open Source); curl, scp, sftp (MIT/X derivative); egrep, fgrep, grep, gzip, gunzip (2-clause BSD); cat, chflag, compress, cp, date, echo, env, link, ln, printenv, pwd, sed, tar, uncompress, uptime (3-clause BSD); chgrp, chksum, chmod, chown, df, du, groups, id, ls, mkdir, mv, readlink, rm, rmdir, stat, sum, touch, tr, uname, wc, whoami (4-clause BSD). By Nicolas Holzschuh.</li>\n'
            '\t      <li><a href="https://github.com/holzschu/network_ios">network_ios</a> — by Nicolas Holzschuh.</li>\n'
            '\t      <li>Source Code Pro Font — SIL Open Font License 1.1; © 2010, 2012 Adobe Systems Inc.</li>\n'
            '\t      <li>DejaVu Sans Mono Font — DejaVu Fonts License 1.0; © Roy Y.T. Chen.</li>\n'
            '\t      <li>Roboto Mono — Apache License 2.0; © Google Inc.</li>\n'
            '\t      <li><a href="http://www.entypo.com">Entypo pictograms</a> — <a href="http://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>; by Bruce Daniel.</li>\n'
            '\t    </ul>\n'
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
