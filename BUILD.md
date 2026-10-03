# Building HermesLink

This repository stores Hermes/iSH integration code and Blink customization
scripts, not Blink app or framework source. The upstream Blink revision is pinned in
`hermes/blink/UPSTREAM_REVISION`; app glue and assets are in
`hermes/blink/overlay/`, and changes to upstream files are applied by small
per-file Python scripts in `hermes/blink/patches/`.

## Prepare Blink locally

Requirements: macOS with Xcode and command-line tools, Git, and the dependencies
required by the upstream Blink build.

```sh
git clone https://github.com/blinksh/blink.git /tmp/blink-source
git -C /tmp/blink-source checkout "$(tr -d '\r\n' < hermes/blink/UPSTREAM_REVISION)"
git -C /tmp/blink-source submodule update --init --recursive
bash hermes/build/prepare-blink-source.sh /tmp/blink-source "$PWD"
./get_frameworks.sh
./get_resources.sh
cp template_setup.xcconfig developer_setup.xcconfig
```

The preparation script rejects any checkout that does not match the pinned
revision, applies the overlay and Python patch scripts, and materializes the
Blink tree in the repository checkout. CI performs the same preparation before
building the app.
The staged Blink files are ignored by Git; they are generated build inputs, not
repository sources.

After preparation, open `Blink.xcodeproj`, configure the developer identity,
and build the `Blink` scheme. Refer to the Xcode and dependency requirements of
the pinned upstream Blink revision.

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
  `TerminalViewController.m` starts an interactive session. Rootfs mounting
  remains in its upstream rootfs initcall, while `FsInitialize` is deferred to
  a late initcall so session startup waits for PTY/device initialization too.
  Workqueue submissions before `call_block_init` can hit the upstream hard-trap
  path.
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
- **Documents mount** — Documents is not mounted automatically. Each prepared
  rootfs contains `/ish/mount-documents.sh` (under a generated `/ish`
  directory); run it inside iSH when you want the
  Files-visible Documents directory mounted at `/mnt/documents`. The script
  mounts the host directory directly with `documentsfs`, without fakefs
  `meta.db`. Regular files appear as `0666 & ~0022` and directories as
  `0777 & ~0022`; ownership, chmod/chown, hard-link creation, and symlinks are
  not supported. The mask can be changed for the active mount with
  `mount -o remount,mask=0027 /mnt/documents`.
- **iSH networking** — iSH guest sockets use iOS networking. The app prepares
  and indexes the host-backed `/etc/resolv.conf` in the profile before kernel
  startup, then writes iOS DNS servers there at startup and when network
  reachability changes; the guest kernel does not write the resolver file.
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
