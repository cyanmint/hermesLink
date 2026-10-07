# HermesLink

HermesLink is a Blink-based iOS terminal with an embedded Hermes Agent and an
optional Alpine Linux guest powered by iSH. The sections below cover the
HermesLink features and controls added to the app.

## First run

1. Open HermesLink and create a terminal.
2. Run `hermes model` and follow the prompts to choose a model provider and
   authenticate. Keep provider credentials private; do not paste keys into
   commands, shared workspaces, or chat.
3. Start a Hermes conversation with `hermes`. You can also launch Hermes WebUI
   with `hermes webui`.

The app's default workspace is `Documents`. To work in another directory, open
the WebUI workspace controls and add or select that directory; the initial
terminal workspace is also `Documents`. It is visible in the iOS Files app under
**On My iPhone/iPad → HermesLink** (the exact display name may vary by iOS
version). Files you create there remain available after restarting the app.
Hermes Agent and WebUI state are kept separately under `Documents/HermesHome`.

## Settings and gestures

In a terminal, swipe up with three fingers to open Settings. In the HermesLink
section:

- **Start WebUI when opening** controls whether the WebUI opens automatically
  when a terminal is opened. It is enabled by default.
- **Open WebUI in foreground** controls whether the WebUI's server terminal is
  shown while it runs. Leave this on if you need to see server output.
- **App, Term and WebUI logs** enables or disables HermesLink diagnostics. Logs
  are written to `Documents/hermeslink.log`; the toggle is on by default.

Swipe down with three fingers to open the WebUI. You can also run
`hermes webui --host 127.0.0.1 --port 8787`; the local server is available at
`http://127.0.0.1:8787` on the device.

## Using terminal and iSH

The `terminal` tool runs commands in Blink's iOS `ios_system` shell. It is not a
Linux or macOS machine: available commands and system interfaces are limited,
and background processes and interactive PTY sessions are not supported by
Hermes Agent's iOS terminal integration. Use it for foreground shell commands
and files in the current workspace.

Use `ish` when a task needs a real Linux kernel/userland, Alpine packages, or
Linux-specific tools. For example:

```sh
ish uname -a
ish apk add git
ish git --version
```

The iSH guest has its own persistent root filesystem profile. Manage profiles
from **Settings → iSH → Rootfs Profiles** or with the `ishfs` shell command.
Changing the active profile takes effect the next time the iSH kernel starts;
force-quit and reopen HermesLink if iSH has already run in the current app
session. The guest does not automatically see the app's Documents directory.
When needed, run this inside iSH:

```sh
/ish/mount-documents.sh
```

The helper mounts Documents at `/mnt/documents`. The host-backed mount has
limited filesystem semantics; it is not a general Linux filesystem.

The host shell includes a WebKit-based WASI runtime. Use `wasm file.wasm` to
run a WebAssembly module and `pkg list` to see the available downloads.
`pkg install <name>` installs a curated module from a-Shell-commands into
`Documents/bin`; installed command names are added to the shell at app startup.
WASI runs with a virtual copy of the current Documents workspace, and changed
files are written back there. Interactive terminal input, sockets, and process
spawning are not available to WASI modules.

`Documents/bin` is added to `PATH`. Run `pkg install llvm-22` to download the
upstream LLVM/clang C SDK into `Documents/Library`, matching a-Shell's setup.
This SDK does not include the clang compiler executable. The `clang` command
displays a-Shell's C SDK hint and can run a user-provided `clang.wasm` from
`Documents/bin`. Review upstream package licenses before installing commands.
The native Python runtime is available as both `python` and `python3`. Use
`export NAME=value` to export shell variables; running `sh` starts a nested
shell that exits with `exit`.

User-provided `Documents/bin/<name>.wasm` modules are registered as shell
commands named `<name>`; for example, `clang.wasm` is invoked as `clang`. The
pinned a-Shell-commands release does not provide a `clang.wasm` asset, so `pkg`
installs the C SDK separately and does not claim to install a clang compiler.

The Agent's `ish` tool runs foreground commands only, with a default timeout of
180 seconds and a maximum of 600 seconds. It cannot provide an interactive
terminal session or leave a command running in the background.

## Add the HermesLink skill

This repository includes [`SKILL.md`](SKILL.md), a set of instructions that
helps Hermes Agent choose between the limited iOS terminal and the Linux guest.
To install it, save the file in the Hermes skills directory in Files:

`HermesLink/Documents/HermesHome/skills/hermeslink-ios/SKILL.md`

Create the `hermeslink-ios` folder if it does not exist, then start a new Hermes
conversation. To verify the skill is available, run `hermes skills list`.

## More information

- [DEVELOP.md](DEVELOP.md) explains the repository layout and how developers
  prepare and build HermesLink.
- [COPYING.md](COPYING.md) describes project attribution and links to upstream
  component licenses.
- [AUTHORS](AUTHORS) records authorship and the AI-generation notice.
