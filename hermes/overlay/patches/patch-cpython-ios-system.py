#!/usr/bin/env python3
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Patch pinned CPython sources to route iOS process calls through ios_system.

The bridge follows the ios_system integration technique in holzschu/cpython
commit 0c3aa6418f2f8d874e1be62e45226af002bbcc8d; CPython itself remains pinned
by build-native-ios.sh and is not replaced with that fork.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

MARKER = "HERMESLINK_IOS_SYSTEM_BRIDGE_V1"
BRIDGE_SOURCE = Path(__file__).resolve().parents[1] / "cpython" / "ios_system_bridge.h"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"cannot read CPython source {path}: {exc}") from exc


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label} anchor expected once, found {count}")
    return text.replace(old, new, 1)


def patch_subprocess(path: Path) -> None:
    text = _read(path)
    platform_guard = '_can_fork_exec = sys.platform not in {"emscripten", "wasi", "ios", "tvos", "watchos"}\n'
    disabled_comment = (
        f"# {MARKER}: iOS subprocess.Popen remains disabled; "
        "ios_system virtual processes do not provide POSIX fork/exec semantics.\n"
    )
    if MARKER in text:
        if platform_guard not in text:
            legacy_assignment = '_can_fork_exec = sys.platform not in {"emscripten", "wasi", "tvos", "watchos"}\n'
            if legacy_assignment not in text:
                raise SystemExit("legacy subprocess iOS fork guard not found")
            text = text.replace(legacy_assignment, platform_guard + disabled_comment, 1)
            legacy_comment = f"# {MARKER}: iOS uses ios_system virtual processes, never libc fork/exec.\n"
            text = text.replace(legacy_comment, "", 1)
        old_spawn_override = (
            'if sys.platform == "ios":\n'
            "    # Route iOS Popen through the patched _posixsubprocess bridge.\n"
            "    _USE_POSIX_SPAWN = False\n"
        )
        text = text.replace(old_spawn_override, "", 1)
        old_capability_guard = '''        if sys.platform == "ios" and (
            preexec_fn is not None or start_new_session
            or process_group not in (None, -1) or pass_fds
            or user is not None or group is not None or extra_groups is not None
            or umask >= 0
        ):
            raise OSError(
                errno.ENOTSUP,
                "iOS ios_system subprocess bridge does not support process groups, "
                "preexec_fn, pass_fds, credential changes, or umask overrides",
            )
'''
        text = text.replace(old_capability_guard, "", 1)
        if "if not _can_fork_exec:" not in text:
            raise SystemExit("subprocess iOS Popen restriction anchor not found")
        _write(path, text)
        return
    if platform_guard not in text or "if not _can_fork_exec:" not in text:
        raise SystemExit("subprocess iOS Popen restriction anchor not found")
    text = text.replace(
        platform_guard,
        platform_guard + disabled_comment,
        1,
    )
    _write(path, text)


def patch_posixmodule(path: Path) -> None:
    text = _read(path)
    if MARKER in text:
        return

    text = _replace_once(
        text,
        '#include "Python.h"\n',
        '#include "Python.h"\n#include "ios_system_bridge.h" /* ' + MARKER + ' */\n',
        "posixmodule bridge include",
    )
    text = _replace_once(
        text,
        "#  include <sys/mount.h>\n#endif\n",
        "#  include <sys/mount.h>\n"
        "#  if TARGET_OS_IPHONE && !defined(HAVE_SYSTEM)\n"
        "#    define HAVE_SYSTEM 1\n"
        "#  endif\n"
        "#endif\n",
        "posixmodule iOS os.system availability",
    )
    text = _replace_once(
        text,
        "    result = system(bytes);\n",
        "#if TARGET_OS_IPHONE\n"
        "    result = hermes_ios_system(bytes);\n"
        "#else\n"
        "    result = system(bytes);\n"
        "#endif\n",
        "posixmodule os.system dispatch",
    )
    text = _replace_once(
        text,
        "        res = waitpid(pid, &status, options);\n",
        "#if TARGET_OS_IPHONE\n"
        "        res = hermes_ios_waitpid(pid, &WAIT_STATUS_INT(status), options);\n"
        "#else\n"
        "        res = waitpid(pid, &status, options);\n"
        "#endif\n",
        "posixmodule os.waitpid dispatch",
    )
    _write(path, text)


def _function_start(lines: list[str], name: str, return_type: str) -> int:
    for index, line in enumerate(lines[:-1]):
        stripped = line.strip()
        if stripped.startswith(f"static void {name}(") or stripped.startswith(f"static pid_t {name}("):
            return index
        if stripped == return_type and lines[index + 1].lstrip().startswith(name + "("):
            return index
        if stripped.startswith(f"{return_type} {name}("):
            return index
    raise SystemExit(f"_posixsubprocess {name} function anchor not found")


def _function_end(lines: list[str], start: int) -> int:
    depth = 0
    opened = False
    for index in range(start + 1, len(lines)):
        for char in lines[index]:
            if char == "{":
                depth += 1
                opened = True
            elif char == "}" and opened:
                depth -= 1
                if depth == 0:
                    return index + 1
    raise SystemExit("_posixsubprocess function end not found")


def _guard_parent_pipe_close(lines: list[str], name: str) -> None:
    condition = f"if ({name} != -1)"
    call = f"POSIX_CALL(close({name}));"
    for index, line in enumerate(lines):
        indent = line[:len(line) - len(line.lstrip())]
        if line.strip().startswith(condition + " ") and call in line:
            lines[index:index + 1] = [
                f"{indent}#if !TARGET_OS_IPHONE",
                f"{indent}{condition}",
                f"{indent}    {call}",
                f"{indent}#endif",
            ]
            return
        if line.strip() != condition:
            continue
        call_index = index + 1
        while call_index < len(lines) and not lines[call_index].strip():
            call_index += 1
        if call_index >= len(lines) or lines[call_index].strip() != call:
            continue
        call_indent = lines[call_index][:len(lines[call_index]) - len(lines[call_index].lstrip())]
        lines[index:call_index + 1] = [
            f"{indent}#if !TARGET_OS_IPHONE",
            f"{indent}{condition}",
            f"{call_indent}{call}",
            f"{indent}#endif",
        ]
        return
    raise SystemExit(f"_posixsubprocess parent close({name}) anchor not found")


def _matching_brace(lines: list[str], start_line: int, start_column: int) -> int:
    depth = 0
    for line_index in range(start_line, len(lines)):
        source = lines[line_index][start_column:] if line_index == start_line else lines[line_index]
        for char in source:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return line_index
    raise SystemExit("_posixsubprocess block closing brace not found")


def _patch_child_exec(lines: list[str]) -> list[str]:
    start = _function_start(lines, "child_exec", "Py_NO_INLINE static void")
    end = _function_end(lines, start)
    segment = lines[start:end]
    for name in ("p2cwrite", "c2pread", "errread"):
        _guard_parent_pipe_close(segment, name)

    errpipe_line = "POSIX_CALL(close(errpipe_read));"
    errpipe_indices = [i for i, line in enumerate(segment) if line.strip() == errpipe_line]
    if len(errpipe_indices) != 1:
        raise SystemExit("_posixsubprocess close(errpipe_read) anchor expected once")
    index = errpipe_indices[0]
    indent = segment[index][:len(segment[index]) - len(segment[index].lstrip())]
    segment[index:index + 1] = [
        f"{indent}#if !TARGET_OS_IPHONE",
        f"{indent}{errpipe_line}",
        f"{indent}#endif",
    ]

    for index, line in enumerate(segment):
        segment[index] = line.replace("POSIX_CALL(dup2(", "POSIX_CALL(HERMES_SUBPROCESS_DUP2(")
        segment[index] = segment[index].replace("chdir(cwd)", "HERMES_SUBPROCESS_CHDIR(cwd)")
        segment[index] = segment[index].replace("if (restore_signals) {", "if (restore_signals && !TARGET_OS_IPHONE) {")
        segment[index] = segment[index].replace("if (call_setsid)", "if (call_setsid && !TARGET_OS_IPHONE)")
        segment[index] = segment[index].replace("if (pgid_to_set >= 0)", "if (pgid_to_set >= 0 && !TARGET_OS_IPHONE)")
        segment[index] = segment[index].replace("if (child_umask >= 0)", "if (child_umask >= 0 && !TARGET_OS_IPHONE)")
        segment[index] = segment[index].replace("if (extra_group_size >= 0)", "if (extra_group_size >= 0 && !TARGET_OS_IPHONE)")
        segment[index] = segment[index].replace("if (gid != (gid_t)-1)", "if (gid != (gid_t)-1 && !TARGET_OS_IPHONE)")
        segment[index] = segment[index].replace("if (uid != (uid_t)-1)", "if (uid != (uid_t)-1 && !TARGET_OS_IPHONE)")
        segment[index] = segment[index].replace(
            "if (preexec_fn != Py_None && preexec_fn_args_tuple)",
            "if (preexec_fn != Py_None && preexec_fn_args_tuple && !TARGET_OS_IPHONE)",
        )
        segment[index] = segment[index].replace("if (close_fds) {", "if (close_fds && !TARGET_OS_IPHONE) {")
        segment[index] = segment[index].replace(
            "if (close_fds) _close_open_fds(",
            "if (close_fds && !TARGET_OS_IPHONE) _close_open_fds(",
        )

    loop_start = next(
        (i for i, line in enumerate(segment) if "for (" in line and "exec_array[i]" in line),
        None,
    )
    if loop_start is None:
        raise SystemExit("_posixsubprocess exec loop anchor not found")
    loop_open = segment[loop_start].find("{")
    if loop_open < 0:
        raise SystemExit("_posixsubprocess exec loop opening brace not found")
    loop_end = _matching_brace(segment, loop_start, loop_open)
    loop = "\n".join(segment[loop_start:loop_end + 1])
    if "execve(" not in loop or "execv(" not in loop:
        raise SystemExit("_posixsubprocess exec loop body did not match CPython")
    replacement = [
        "#if TARGET_OS_IPHONE",
        "    errno = 0;",
        "    if (exec_array[0] == NULL) {",
        "        errno = ENOENT;",
        "        goto error;",
        "    }",
        "    saved_errno = envp",
        "        ? hermes_ios_execve(exec_array[0], argv, envp)",
        "        : hermes_ios_execv(exec_array[0], argv);",
        "    if (saved_errno >= 0) return;",
        "    saved_errno = errno ? errno : ENOEXEC;",
        "#else",
        *loop.splitlines(),
        "#endif",
    ]
    segment[loop_start:loop_end + 1] = replacement

    return lines[:start] + segment + lines[end:]


def patch_posixsubprocess(path: Path) -> None:
    text = _read(path)
    if MARKER in text:
        return
    text = _replace_once(
        text,
        '#include "Python.h"\n',
        '#include "Python.h"\n#include "ios_system_bridge.h" /* ' + MARKER + ' */\n'
        "#if TARGET_OS_IPHONE\n"
        "#  define HERMES_SUBPROCESS_DUP2 hermes_ios_dup2\n"
        "#  define HERMES_SUBPROCESS_CHDIR hermes_ios_chdir\n"
        "#else\n"
        "#  define HERMES_SUBPROCESS_DUP2 dup2\n"
        "#  define HERMES_SUBPROCESS_CHDIR chdir\n"
        "#endif\n",
        "_posixsubprocess bridge include",
    )
    text = "\n".join(_patch_child_exec(text.splitlines())) + "\n"

    lines = text.splitlines()
    start = _function_start(lines, "do_fork_exec", "Py_NO_INLINE static pid_t")
    end = _function_end(lines, start)
    segment = lines[start:end]
    fork_indices = [i for i, line in enumerate(segment) if line.strip() == "pid = fork();"]
    if not fork_indices:
        raise SystemExit("_posixsubprocess fork anchor not found")
    fork_index = fork_indices[-1]
    fork_indent = segment[fork_index][:len(segment[fork_index]) - len(segment[fork_index].lstrip())]
    segment[fork_index:fork_index + 1] = [
        f"{fork_indent}#if TARGET_OS_IPHONE",
        f"{fork_indent}if (!hermes_ios_subprocess_enabled(envp)) {{",
        f"{fork_indent}    errno = ENOTSUP;",
        f"{fork_indent}    return -1;",
        f"{fork_indent}}}",
        f"{fork_indent}pid = hermes_ios_fork();",
        f"{fork_indent}if (pid == (pid_t)-1) return -1;",
        f"{fork_indent}#else",
        f"{fork_indent}pid = fork();",
        f"{fork_indent}#endif",
    ]
    segment = [line.replace("if (pid != 0)", "if (pid != 0 && !TARGET_OS_IPHONE)") for line in segment]

    exit_index = next((i for i, line in enumerate(segment) if line.strip() == "_exit(255);"), None)
    if exit_index is None:
        raise SystemExit("_posixsubprocess parent exit anchor not found")
    exit_indent = segment[exit_index][:len(segment[exit_index]) - len(segment[exit_index].lstrip())]
    end_count = 2 if exit_index + 1 < len(segment) and segment[exit_index + 1].strip() == "return 0;" else 1
    segment[exit_index:exit_index + end_count] = [
        f"{exit_indent}#if TARGET_OS_IPHONE",
        f"{exit_indent}return pid;",
        f"{exit_indent}#else",
        f"{exit_indent}_exit(255);",
        f"{exit_indent}return 0;",
        f"{exit_indent}#endif",
    ]
    lines[start:end] = segment
    _write(path, "\n".join(lines) + "\n")


def patch_native_tree(root: Path) -> None:
    if not BRIDGE_SOURCE.is_file():
        raise SystemExit(f"missing CPython ios_system bridge header: {BRIDGE_SOURCE}")
    modules = root / "Modules"
    modules.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BRIDGE_SOURCE, modules / "ios_system_bridge.h")
    patch_posixmodule(modules / "posixmodule.c")
    patch_subprocess(root / "Lib" / "subprocess.py")


def patch_stdlib_tree(root: Path) -> None:
    patch_subprocess(root / "subprocess.py")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdlib-only", action="store_true", help="patch a staged Python stdlib root")
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args()
    if args.stdlib_only:
        patch_stdlib_tree(args.source_root)
    else:
        patch_native_tree(args.source_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
