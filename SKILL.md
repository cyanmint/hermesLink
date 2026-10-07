---
name: hermeslink-ios-terminal
description: Choose between HermesLink's limited iOS terminal and its persistent Alpine Linux guest, and move files safely between them.
---

# HermesLink terminal and iSH

HermesLink has two separate command environments:

- `terminal` runs registered commands in Blink's iOS `ios_system` environment.
- `ish` runs shell commands in a persistent Alpine Linux guest.

Choose the environment before running a command. Do not assume `terminal` is a
Linux or macOS shell.

## Commands available in `terminal`

The Blink command registry provides these app commands:

| Command | Purpose |
| --- | --- |
| `bench` | Run Blink's benchmark command. |
| `browse` | Open Blink's browser interface. |
| `build` | Invoke Blink's build command. |
| `clear` | Clear terminal output. |
| `code` | Open Blink's code interface. |
| `clang` | Run a user-provided `Documents/bin/clang.wasm`, or print C SDK setup guidance. |
| `config` | View or change Blink configuration. |
| `device-info` | Show device information. |
| `facecam` | Use Blink's face-camera command. |
| `fcp` | Blink file-transfer command. |
| `geo` | Show or use location-related information. |
| `help` | Show Blink command help. |
| `hermes` | Run Hermes Agent and its subcommands, such as `hermes webui`. |
| `history` | View or manage command history. |
| `ish` | Run a command in the Alpine Linux guest. |
| `ishfs` | Manage iSH rootfs profiles. |
| `mosh1` | Mosh protocol helper. |
| `open` | Open a file using Blink's file-opening support. |
| `openurl` | Open a URL. |
| `pkg` | List or install supported WASI packages and the LLVM/clang C SDK. |
| `python` | Run the embedded Python runtime. |
| `python3` | Alias for the embedded Python runtime. |
| `say` | Speak text using Blink's speech command. |
| `scp` | Secure-copy file-transfer command. |
| `sftp` | Secure file-transfer command. |
| `sh` | Run Blink's registered shell interpreter. |
| `showkey` | Display keyboard input information. |
| `skstore` | Blink secure-store command. |
| `ssh` | Connect to a host using SSH. |
| `ssh-add` | Add SSH identities to the agent. |
| `ssh-agent` | Start or manage the SSH agent. |
| `udptunnel` | Run Blink's UDP tunnel command. |
| `wasm` | Run a WebAssembly module with WASI. |
| `whatsnew` | Show Blink's release notes. |
| `xcall` | Invoke Blink's native-call bridge. |
| `export`, `setenv`, `unsetenv`, `printenv` | Set, remove, or inspect environment variables. |

The app also bundles these `ios_system` commands:

`alias`, `awk`, `bc`, `cat`, `cd`, `chflags`, `cksum`, `chmod`, `compress`,
`cp`, `curl`, `date`, `dc`, `diff`, `dig`, `du`, `echo`, `ed`, `egrep`, `env`,
`fgrep`, `find`, `grep`, `gunzip`, `gzip`, `head`, `host`, `ifconfig`, `link`,
`ln`, `ls`, `md5`, `mkdir`, `mv`, `nc`, `nslookup`, `pbcopy`, `pbpaste`, `ping`,
`pwd`, `readlink`, `rlogin`, `rm`, `rmdir`, `sort`, `stat`, `sum`, `tail`,
`tar`, `tee`, `telnet`, `touch`, `tr`, `unalias`, `uname`, `unlink`, `uniq`,
`uncompress`, `uptime`, `wc`, `whoami`, `whois`, `xargs`, and `wol`. Commands
provided or overridden by Blink (such as `open`, `sh`, and the SSH commands)
are listed above. Shell operations also include pipes and input/output
redirection.

This is the bundled host command inventory, not a general Linux environment.
`apk` is not a bundled host command; use `ish` for Alpine/Linux tools. Installing
a `.wasm` file in `Documents/bin` registers the filename
(without `.wasm`) as a host command on the next app launch. `pkg list` shows the
available prebuilt WASI packages.

Use `terminal` for supported, foreground host operations and files in the
current workspace. The Hermes Agent terminal tool does not support background
processes or interactive PTY sessions. If a command is not in the registered
list, switch to `ish` when it is a Linux utility; otherwise explain that the
requested command is not available.

## Using `ish`

`ish` is a real Linux kernel and Alpine userland, separate from the host
terminal. Run a command from `terminal` with `ish` followed by the guest
command:

```sh
ish uname -a
ish apk add git
ish git --version
```

Inside Hermes Agent, use its `ish` tool and provide the guest command in the
`command` argument. `workdir`, if supplied, must be an absolute path in the
guest. Foreground commands wait up to 180 seconds by default and at most 600
seconds. A command that needs to continue in the background can use
`background=true`; interactive input additionally requires `pty=true` and is
managed with `process_manage`. Do not leave a guest process running unless the
task requires it.

The `ishfs` command manages persistent guest rootfs profiles:

```sh
ishfs list
ishfs create <name>
ishfs import <name> <rootfs-folder-or-tar.gz>
ishfs rename <old-name> <new-name>
ishfs use <name>
ishfs delete <name> --yes
```

Deleting a profile permanently removes its guest files. Never delete, replace,
or switch a user's profile without explicit permission. A newly selected
profile takes effect after force-quitting and reopening HermesLink if iSH has
already started during the current app session.

## iSH profiles and the workspace are different

The default host workspace is the app's Files-visible `Documents` directory.
The terminal starts there. Hermes Agent and WebUI state are stored separately
under `Documents/HermesHome`.

iSH profiles are stored separately under `Documents/iSH/<profile-name>` (for
example, `Documents/iSH/Alpine`). Each profile is its own persistent guest
filesystem; it is not the terminal workspace and is not automatically browsable
from the host terminal. Files in the guest remain in that profile when the app
restarts, while files in `Documents` are host workspace files visible in Files.

## Copy files between iSH and the workspace

Documents is not mounted in the guest automatically. In the guest, run the
profile's helper to mount the host's Documents directory at `/mnt/documents`:

```sh
/ish/mount-documents.sh
```

Then copy a guest file or directory into the host workspace. For example:

```sh
mkdir -p /mnt/documents/from-ish
cp -a /etc/alpine-release /mnt/documents/from-ish/
cp -a /path/in/guest /mnt/documents/from-ish/
```

The copied files are now in the host `Documents` directory: they are available
to `terminal`, Hermes Agent's host workspace, and the iOS Files app. To copy a
workspace file into the guest, copy it from `/mnt/documents/...` to a path in
the guest after mounting. The mount is host-backed and has limited filesystem
semantics; use the guest's own filesystem for Linux-specific operations.

## Safe command practices

- Prefer small, read-only inspections before changing files.
- Ask before deleting files, changing active profiles, or installing large
  packages.
- Quote paths containing spaces.
- Keep host paths (`Documents/...`) distinct from guest paths (`/...` and
  `/mnt/documents/...`).
- Do not expose API keys, tokens, or other credentials in command output,
  diagnostics, or generated files.
