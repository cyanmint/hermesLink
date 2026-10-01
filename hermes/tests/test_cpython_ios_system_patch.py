# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH_PATH = ROOT / "hermes" / "overlay" / "patches" / "patch-cpython-ios-system.py"


class CPythonIosSystemPatchTests(unittest.TestCase):
    def test_native_and_zip_builds_apply_the_cpython_overlay(self):
        native_build = (ROOT / "hermes" / "build" / "build-native-ios.sh").read_text(encoding="utf-8")
        zip_build = (ROOT / "hermes" / "build" / "build-hermesrt-zip.sh").read_text(encoding="utf-8")

        self.assertIn('patch-cpython-ios-system.py" "$TARGET_ROOT"', native_build)
        self.assertIn('patch-cpython-ios-system.py" --stdlib-only "$STAGE/python"', zip_build)

    def _cpython_tree(self, root: Path) -> None:
        (root / "Modules").mkdir(parents=True)
        (root / "Lib").mkdir()
        (root / "Modules" / "posixmodule.c").write_text(
            '''#include "Python.h"
#ifdef __APPLE__
#  include <sys/param.h>
#  include <sys/mount.h>
#endif
#include <stdio.h>
#include <stdlib.h>
#ifdef HAVE_SYSTEM
static long
os_system_impl(PyObject *module, PyObject *command)
{
    long result;
    const char *bytes = PyBytes_AsString(command);
    Py_BEGIN_ALLOW_THREADS
    result = system(bytes);
    Py_END_ALLOW_THREADS
    return result;
}
#endif
#ifdef HAVE_WAITPID
static PyObject *
os_waitpid_impl(PyObject *module, pid_t pid, int options)
{
    pid_t res;
    int async_err = 0;
    WAIT_TYPE status;
    WAIT_STATUS_INT(status) = 0;
    do {
        Py_BEGIN_ALLOW_THREADS
        res = waitpid(pid, &status, options);
        Py_END_ALLOW_THREADS
    } while (res < 0 && errno == EINTR && !(async_err = PyErr_CheckSignals()));
    if (res < 0) return (!async_err) ? posix_error() : NULL;
    return Py_BuildValue("Ni", PyLong_FromPid(res), WAIT_STATUS_INT(status));
}
#endif
''',
            encoding="utf-8",
            newline="\n",
        )
        (root / "Modules" / "_posixsubprocess.c").write_text(
            '''#include "Python.h"
#include <unistd.h>
#define POSIX_CALL(call) do { if ((call) == -1) goto error; } while (0)
Py_NO_INLINE static void
child_exec(char *const exec_array[], char *const argv[],
           char *const envp[], const char *cwd,
           int p2cwrite, int c2pread, int errread,
           int errpipe_read, int close_fds, int call_setsid,
           pid_t pgid_to_set)
{
    /* Close parent's pipe ends. */
    if (p2cwrite != -1)
        POSIX_CALL(close(p2cwrite));
    if (c2pread != -1)
        POSIX_CALL(close(c2pread));
    if (errread != -1)
        POSIX_CALL(close(errread));
    POSIX_CALL(close(errpipe_read));
    /* Dup fds for child. */
    POSIX_CALL(dup2(p2cwrite, 0));
    POSIX_CALL(dup2(c2pread, 1));
    POSIX_CALL(dup2(errread, 2));
    if (cwd) {
        if (chdir(cwd) == -1) goto error;
    }
    if (call_setsid) POSIX_CALL(setsid());
    if (pgid_to_set >= 0) POSIX_CALL(setpgid(0, pgid_to_set));
    if (close_fds) {
        _close_open_fds(3, fds_to_keep, fds_to_keep_len);
    }
    saved_errno = 0;
    for (int i = 0; exec_array[i] != NULL; ++i) {
        const char *executable = exec_array[i];
        if (envp) saved_errno = execve(executable, argv, envp);
        else saved_errno = execv(executable, argv);
    }
    /* Report the first exec error, not the last. */
    if (saved_errno) errno = saved_errno;
error:
}
Py_NO_INLINE static pid_t
do_fork_exec(char *const envp[])
{
    pid_t pid;
    {
        pid = fork();
    }
    if (pid != 0) {
        // Parent process.
        return pid;
    }
    child_exec(NULL, NULL, NULL, NULL, -1, -1, -1, -1, 0, 0, -1);
    _exit(255);
    return 0;
}
''',
            encoding="utf-8",
            newline="\n",
        )
        (root / "Lib" / "subprocess.py").write_text(
            '''import errno
import sys
_can_fork_exec = sys.platform not in {"emscripten", "wasi", "ios", "tvos", "watchos"}
def _use_posix_spawn():
    return True
_USE_POSIX_SPAWN = _use_posix_spawn()
def _cleanup():
    pass
class Popen:
    def __init__(self, preexec_fn=None, close_fds=True, start_new_session=False,
                 pass_fds=(), user=None, group=None, extra_groups=None,
                 umask=-1, process_group=None):
        if not _can_fork_exec:
            raise OSError(errno.ENOTSUP, f"{sys.platform} does not support processes.")
        _cleanup()
''',
            encoding="utf-8",
            newline="\n",
        )

    def test_patch_bridges_ios_system_and_popen_without_enabling_fork(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._cpython_tree(root)
            subprocess.run([sys.executable, str(PATCH_PATH), str(root)], check=True)

            posixmodule = (root / "Modules" / "posixmodule.c").read_text(encoding="utf-8")
            posixsubprocess = (root / "Modules" / "_posixsubprocess.c").read_text(encoding="utf-8")
            subprocess_py = (root / "Lib" / "subprocess.py").read_text(encoding="utf-8")
            bridge = (root / "Modules" / "ios_system_bridge.h").read_text(encoding="utf-8")

            self.assertIn("hermes_ios_system(bytes)", posixmodule)
            self.assertIn("hermes_ios_waitpid", posixmodule)
            self.assertIn("hermes_ios_fork", posixsubprocess)
            self.assertIn("hermes_ios_subprocess_enabled(envp)", posixsubprocess)
            self.assertIn("hermes_ios_execve", posixsubprocess)
            self.assertIn("hermes_ios_dup2", posixsubprocess)
            self.assertIn("return dlsym(RTLD_DEFAULT, name);", bridge)
            self.assertIn('hermes_ios_lookup("ios_system")', bridge)
            self.assertIn('_can_fork_exec = sys.platform not in {"emscripten", "wasi", "tvos", "watchos"}', subprocess_py)
            self.assertIn('if sys.platform == "ios":', subprocess_py)
            self.assertIn("_USE_POSIX_SPAWN = False", subprocess_py)
            self.assertIn("iOS ios_system subprocess bridge does not support", subprocess_py)

    def test_stdlib_only_patch_handles_the_runtime_zip_staging_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "python"
            root.mkdir()
            (root / "subprocess.py").write_text(
                '_can_fork_exec = sys.platform not in {"emscripten", "wasi", "ios", "tvos", "watchos"}\n'
                "_USE_POSIX_SPAWN = _use_posix_spawn()\n",
                encoding="utf-8",
                newline="\n",
            )
            subprocess.run([sys.executable, str(PATCH_PATH), "--stdlib-only", str(root)], check=True)
            patched = (root / "subprocess.py").read_text(encoding="utf-8")
            self.assertIn("ios_system virtual processes", patched)
            self.assertIn("_USE_POSIX_SPAWN = False", patched)

    def test_patch_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._cpython_tree(root)
            subprocess.run([sys.executable, str(PATCH_PATH), str(root)], check=True)
            first = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            subprocess.run([sys.executable, str(PATCH_PATH), str(root)], check=True)
            second = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            self.assertEqual(second, first)

    def test_missing_cpython_anchor_fails_instead_of_silently_skipping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._cpython_tree(root)
            (root / "Modules" / "posixmodule.c").write_text("#include <Python.h>\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(PATCH_PATH), str(root)], capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("anchor", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
