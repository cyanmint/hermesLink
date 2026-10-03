# Building
We provide you with two ways to compile and install Blink Shell. This instructions will refer to assembling
a full Blink Shell, compiling libraries and resources yourself. Due to the many dependencies that compose
Blink Shell, this is the recommended but not shortest method.

You can also clone Blink and obtain a "ready to go"
tar.gz with all the dependencies as described in the ["Build" section of the README.md file](README.md#build).

## Requirements
Please note that to compile and install Blink in your personal
devices, you need to comply with Apple Developer Terms and Conditions,
including obtaining a Developer License for that purpose. You will also
need all the XCode command line developer tools and SDKs provided under
a separate license by Apple Inc.
- XCode > 11.0 and XCode command line tools
- Autotools for OSX

## Cloning
Clone Blink into your local repository and make sure to obtain any submodules:
git submodule init
git submodule update

## Dependencies & Requirements
Blink makes use of multiple dependencies that you have to compile
separately before building Blink itself. There are simple scripts available
to perform this operation.
- [Libssh2 for iOS](https://github.com/holzschu/libssh2-for-iOS); Includes OpenSSL.
- [Mosh for iOS](https://github.com/blinksh/build-mosh); Includes Protobuf.

Please note that Blink currently only supports armv64, so compilation for other architectures is not necessary.

### Installation
#### Libraries
The Blink Shell XCode project will look for Library dependencies under the Framework folder. Libssh2 and Mosh for iOS will
also build OpenSSL and Protobuf respectively, both required to work.

To install Libssh2 and OpenSSL in your Blink repository, please copy
the .framework files generated on [Libssh2 for iOS](https://github.com/carloscabanero/libssh2-for-iOS) to the Framework folders.

[Mosh for iOS](https://github.com/blinksh/build-mosh) will compile both protobuf and Mosh for iOS.
After compiling, copy libmoshios.framework AND libprotobuf.a from the build-protobuf/protobuf-version/lib folder.

Blink also makes use of two other projects, which should be automatically downloaded using git submodule
within the same project:
- UICKeyChainStore
- MBProgressHUD

#### Resources
Blink Shell makes use of a web terminal running from JavaScript code and linked at runtime. All the required
resources to bundle the app, like terminal, fonts and themes, must be included under the Resources folder.

Font Style uploads requires [webfonts.js](https://github.com/typekit/webfontloader), but it isn't
needed for Blink to work. Download the file and drop it into Resources folder.

Blink's Terminal is running from JavaScript code linked at runtime.
Most of the available open source terminals can be made to work with Blink,
just by providing a "write" and "signal" functions. An example of this
is provided in the Resources/term.html file. If you use another
terminal.js, edit term.html to match. We have been also successful plugging in other
terminals like [Terminal.js](http://terminal.js.org).

## Compiling
Blink uses a standard .xcodeproj file. Any missing files will be marked in
red, what can be used to test your installation.

To configure the project:
1. Under Targets > Blink > General > Identities set a unique Bundle Identifier.
2. Under Targets > Blink > General > Identities set your Team.
3. You might be requested to accept your profile or setup your developer account
with XCode, follow the proper Apple Developer documentation in that case.
4. If you would like to use HockeyApp, change the scheme to Blink Hockey, and add HockeyID with your AppID string to info.plist.

Make sure "Blink" is the selected Scheme for compilation. As a standard XCode project, just run it with Cmd-R.

## iSH integration status
`bash hermes/build/fetch-ish-source.sh` fetches the pinned upstream iSH source
and Alpine root filesystem into the ignored `hermes/build/external/ish`
directory, then verifies their checksums. HermesLink boots this iSH Linux
kernel once per app process and exposes it as a native `ish <command>` shell
command (not an `ish container` subcommand) and as an `ish` Hermes Agent tool
registered alongside `terminal` in the standard Hermes bundles. The design:

- **Native command** — `Blink/Commands/ish.m` (`ish_main`), registered in
  `Resources/blinkCommandsDictionary.plist`. It joins its arguments into one
  shell command, bridges the guest's pty to the calling ios_system command's
  own `thread_stdin`/`thread_stdout`, and returns the guest command's real
  exit status.
- **Kernel bridge** — `ISHBridge/ish_kernel_bridge.m` boots the pinned
  upstream kernel exactly once (`actuate_kernel()`'s `run_kernel()` never
  returns, so it runs on its own dedicated background thread) and implements
  the "call into iOS from the kernel" side of `LinuxInterop.h`
  (`Terminal_*`, `DefaultRootPath`, `ReportPanic`, `ConsoleLog`,
  `objc_get`/`objc_put`, `async_do_in_ios`) from scratch — it does not reuse
  upstream's own (UIKit/WebKit-backed) `Terminal.m`. Each `ish <command>`
  invocation reuses the already-booted guest via upstream's
  `linux_start_session()`, matching how upstream's own
  `TerminalViewController.m` starts an interactive session. Sessions wait for
  `LinuxRoot.c`'s rootfs initcall signal before submitting work: probing the
  kernel workqueue immediately after creating its thread can hit the upstream
  hard-trap path before its IRQ pipe is initialized.
- **Exit status** — upstream's `linux_start_session()` only reports that a
  guest process *started*, not how it exited, and upstream's own GUI never
  needed that (interactive sessions end when the user closes them, or the
  pty simply hangs up). `ISHBridge/ish_exit_protocol.{h,c}` is original
  protocol/implementation that wraps every guest command in a `trap ... EXIT`
  trailer (so it still fires even if the command calls `exit` itself) that
  emits a short binary sentinel carrying the real exit status, and a
  streaming scanner that strips it back out of the guest's pty output before
  it reaches the user. The one case this cannot recover a status for is the
  command replacing the shell via `exec(2)` — an inherent limitation of any
  wrapper-script approach, documented and handled as its own error case.
- **Guest root / fakefs** — `ISHBridge/ish_rootfs.{h,c}` is an original,
  from-scratch gzip+ustar extractor (zlib + a minimal ustar parser; no
  upstream code reused) that unpacks the pinned, build-time-bundled Alpine
  rootfs archive directly into `Documents/iSH/Alpine/` on first use, then
  converts it to upstream fakefs's required `data/` plus `meta.db` layout.
  Every named profile is stored in its own Files-visible directory below
  `Documents/iSH/`. Existing direct Alpine rootfs installations,
  `Documents/iSH/Profiles/` profiles, and profiles from
  `Documents/iSH-Profiles/` are migrated there without overwriting conflicting
  data. The converter preserves guest modes in iSH's
  metadata database while making host-backed data writable and encodes
  symlinks in the representation fakefs expects. The extractor leaves
  directories writable while extracting their contents, then restores the
  archive's directory modes. Raw imported rootfs folders/archives and existing
  legacy profiles are converted before the kernel starts. Nonempty invalid
  profiles are preserved and reported with instructions to delete/recreate or
  import a valid rootfs; they are never silently overwritten. Profiles are
  checked for the required init program before boot so a missing fakefs root
  cannot escalate into the kernel's panic/trap path,
  validating every entry with `ISHBridge/ish_path_safety.{h,c}` (rejects
  absolute paths and `..` components, and refuses to traverse through an
  existing non-directory/symlink path component) before touching the
  filesystem. The persistent, on-disk result is what makes the guest
  *persistent*: packages/files a user's commands create survive app
  relaunches, even though in-memory kernel/process state does not.
- **Rootfs profiles** — `ishfs` supports `list`, `create`, `import`, `rename`,
  `delete`, and `use`. Creating copies the active rootfs; imports accept a
  complete rootfs folder or `.tar.gz`/`.tgz` archive. The Settings → iSH page
  provides the same profile operations. Selecting another profile takes
  effect on the next kernel start; force-quit and reopen Blink if `ish` has
  already started in the current app process.
- **Hermes Agent tool** — `hermes/overlay/hermes/tools/ish_tool.py` registers
  an `ish` tool that reuses the exact same native `_hermesios` async-process
  bridge the `terminal` tool's iOS backend uses, just pointed at the native
  `ish` command instead of `sh -c`.
  `hermes/overlay/patches/patch-ish-tool.py` adds `"ish"` to the shared
  `_HERMES_CORE_TOOLS` list in hermes-agent's `toolsets.py` (applied to a
  *staged copy* at build time, never the ignored upstream checkout), so
  every standard Hermes bundle that already includes `terminal` —
  `hermes-cli`, `hermes-telegram`, the `coding` posture, etc. — picks up
  `ish` the same way.
- **Native framework build** — the Linux `build-ish-meson` CI stage
  cross-compiles the upstream kernel, fakefs, and emulator Meson/Ninja
  archives for iOS, then publishes the Meson build, pinned source checkout,
  and cross-toolchain as `ISHMesonBuild.tar.gz` on the fixed GitHub Release.
  The macOS `build-ish-runtime` stage downloads that release asset, reuses
  the Linux build tree, builds the iOS host-interoperability Xcode targets,
  and links those archives plus the HermesLink bridge into a dynamic
  `Ish.framework`. The resulting framework is published in
  `ISHLinuxNative.zip` together with the pinned Alpine rootfs. The app archive
  job installs that real framework and verifies/embeds the pinned rootfs,
  enables `ISH_NATIVE_AVAILABLE=YES`, and builds against the actual kernel.
  Only the temporary Hermes runtime framework and `hermesrt.zip` are omitted
  from the app component; IPA assembly adds the actual Hermes runtime and
  signs the app, retaining the real iSH framework and rootfs. This mirrors the
  HermesRuntime.framework link/embed path while keeping the guest kernel out
  of Blink's own linker inputs. Native HermesRuntime.framework is also
  cross-compiled on Linux; the app archive and IPA assembly remain macOS jobs.
- **Switchable link, safe default** — `hermes/build/ISHNative.xcconfig`
  (included from `template_setup.xcconfig`) defaults
  `ISH_NATIVE_AVAILABLE` to `NO`, which compiles
  `ISHBridge/ish_kernel_bridge_stub.m` (keeps `ish` registered everywhere,
  reporting the guest kernel as unavailable) instead of linking
  `Ish.framework`. CI app builds explicitly set `ISH_NATIVE_AVAILABLE=YES`
  only after installing the real framework and pinned rootfs; standalone
  checkouts without those build artifacts retain the safe stub default.

The fetched iSH source includes its GPLv3 and iOS additional-term notices;
those licenses must be preserved in any eventual linked distribution.
