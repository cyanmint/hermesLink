#!/usr/bin/env python3
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Make PTY initialization safe and defer session readiness until late initcalls."""

from __future__ import annotations

import sys
from pathlib import Path


PTY_SOURCE = Path("app/LinuxPTY.c")
INTEROP_SOURCE = Path("app/LinuxInterop.c")
ROOT_SOURCE = Path("app/LinuxRoot.c")
ROOT_DOCUMENTS_DECLARATION = "void FsInitialize(void);"
ROOT_DOCUMENTS_DECLARATION_PATCHED = """void FsInitialize(void);
const char *DefaultDocumentsPath(void);
const char *DefaultDocumentsMountPath(void);
unsigned int DefaultDocumentsMask(void);

static __init void ish_mount_documents(void) {
    const char *source = DefaultDocumentsPath();
    const char *point = DefaultDocumentsMountPath();
    if (source == NULL || source[0] == '\\0' ||
        point == NULL || point[0] != '/' || point[1] == '\\0')
        return;

    char mountpoint[256];
    strlcpy(mountpoint, point, sizeof(mountpoint));
    int err;
    for (char *cursor = mountpoint + 1; ; cursor++) {
        if (*cursor != '/' && *cursor != '\\0')
            continue;
        char separator = *cursor;
        *cursor = '\\0';
        err = init_mkdir(mountpoint, 0755);
        *cursor = separator;
        if (err < 0 && err != -EEXIST) {
            pr_warn("ish: could not create Documents mount point %s: %s\\n",
                    mountpoint, errname(err));
            return;
        }
        if (separator == '\\0')
            break;
    }

    char options[32];
    snprintf(options, sizeof(options), "mask=%04o", DefaultDocumentsMask() & 0777);
    err = do_mount(source, point, "documentsfs", MS_SILENT, options);
    if (err < 0)
        pr_warn("ish: could not mount Documents at %s: %s\\n",
                point, errname(err));
}"""
ROOT_MOUNT_CALL = '    init_chroot(".");\n\n    FsInitialize();'
ROOT_MOUNT_CALL_PATCHED = '    init_chroot(".");\n    ish_mount_documents();\n\n    FsInitialize();'
PTY_PATH_DECLARATION = "static struct path ptmx_path;"
PTY_PATH_DECLARATION_PATCHED = """static struct path ptmx_path;
static int ios_pty_ensure_initialized(void);"""

PTY_INIT = """static __init int ios_pty_init(void) {
    init_mkdir("/dev/pts", 0755);
    int err = do_mount("devpts", "/dev/pts", "devpts", MS_SILENT, NULL);
    if (err < 0) {
        panic("ish: failed to mount devpts: %s", errname(err));
    }
    err = kern_path("/dev/pts/ptmx", 0, &ptmx_path);
    if (err < 0) {
        panic("ish: failed to acquire ptmx: %s", errname(err));
    }
    return 0;
}

device_initcall(ios_pty_init);"""

PTY_INIT_PATCHED = """static int ios_pty_ensure_initialized(void) {
    if (ptmx_path.mnt != NULL && ptmx_path.dentry != NULL)
        return 0;

    int err = kern_path("/dev/pts/ptmx", 0, &ptmx_path);
    if (err == 0)
        return 0;

    init_mkdir("/dev/pts", 0755);
    err = do_mount("devpts", "/dev/pts", "devpts", MS_SILENT, NULL);
    if (err < 0) {
        int lookup_err = kern_path("/dev/pts/ptmx", 0, &ptmx_path);
        return lookup_err < 0 ? err : 0;
    }
    return kern_path("/dev/pts/ptmx", 0, &ptmx_path);
}

static int __init ios_pty_init(void) {
    int err = ios_pty_ensure_initialized();
    if (err < 0)
        panic("ish: failed to initialize devpts: %s", errname(err));
    return 0;
}
device_initcall(ios_pty_init);"""

PTY_OPEN = """struct file *ios_pty_open(nsobj_t *terminal_out) {
    struct file *ptm_file = dentry_open(&ptmx_path, O_RDWR, current_cred());"""

PTY_OPEN_PATCHED = """struct file *ios_pty_open(nsobj_t *terminal_out) {
    int err = ios_pty_ensure_initialized();
    if (err < 0)
        return ERR_PTR(err);

    struct file *ptm_file = dentry_open(&ptmx_path, O_RDWR, current_cred());"""

SESSION_TTY = """    session->tty = ios_pty_open(&session->terminal);
    session->callback = done;"""

SESSION_TTY_PATCHED = """    session->tty = ios_pty_open(&session->terminal);
    if (IS_ERR(session->tty)) {
        int err = PTR_ERR(session->tty);
        kfree(session);
        done(err, 0, NULL);
        return;
    }
    session->callback = done;"""

ROOTFS_INITCALL = """    FsInitialize();
    return 0;
}

rootfs_initcall(ish_rootfs);"""

ROOTFS_INITCALL_PATCHED = """    return 0;
}

static __init int ish_session_ready(void) {
    FsInitialize();
    return 0;
}

rootfs_initcall(ish_rootfs);
late_initcall(ish_session_ready);"""


def replace_once(source: str, before: str, after: str, filename: Path) -> str:
    if after in source:
        return source
    if source.count(before) != 1:
        raise ValueError(f"unexpected pinned source layout in {filename}")
    return source.replace(before, after, 1)


def patch(source_root: Path) -> None:
    pty_path = source_root / PTY_SOURCE
    interop_path = source_root / INTEROP_SOURCE
    root_path = source_root / ROOT_SOURCE
    pty = pty_path.read_text(encoding="utf-8")
    interop = interop_path.read_text(encoding="utf-8")
    root = root_path.read_text(encoding="utf-8")
    if ROOT_DOCUMENTS_DECLARATION_PATCHED not in root:
        if root.count(ROOT_DOCUMENTS_DECLARATION) != 1:
            raise ValueError(f"unexpected pinned source layout in {ROOT_SOURCE}")
        root = root.replace(
            ROOT_DOCUMENTS_DECLARATION,
            ROOT_DOCUMENTS_DECLARATION_PATCHED,
            1,
        )
    root = replace_once(root, ROOT_MOUNT_CALL, ROOT_MOUNT_CALL_PATCHED, ROOT_SOURCE)
    root = replace_once(root, ROOTFS_INITCALL, ROOTFS_INITCALL_PATCHED, ROOT_SOURCE)
    if PTY_PATH_DECLARATION_PATCHED not in pty:
        if pty.count(PTY_PATH_DECLARATION) != 1:
            raise ValueError(f"unexpected pinned source layout in {PTY_SOURCE}")
        pty = pty.replace(
            PTY_PATH_DECLARATION,
            PTY_PATH_DECLARATION_PATCHED,
            1,
        )
    pty = replace_once(pty, PTY_INIT, PTY_INIT_PATCHED, PTY_SOURCE)
    pty = replace_once(pty, PTY_OPEN, PTY_OPEN_PATCHED, PTY_SOURCE)
    interop = replace_once(interop, SESSION_TTY, SESSION_TTY_PATCHED, INTEROP_SOURCE)
    root = replace_once(root, ROOTFS_INITCALL, ROOTFS_INITCALL_PATCHED, ROOT_SOURCE)
    pty_path.write_text(pty, encoding="utf-8")
    interop_path.write_text(interop, encoding="utf-8")
    root_path.write_text(root, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch-ish-pty.py <pinned-ish-source-root>", file=sys.stderr)
        return 2
    try:
        patch(Path(sys.argv[1]))
    except (OSError, ValueError) as error:
        print(f"patch-ish-pty.py: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
