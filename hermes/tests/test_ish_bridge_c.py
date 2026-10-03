# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Compiles and exercises the portable ISHBridge C modules (ish_path_safety,
ish_rootfs, ish_exit_protocol). These modules contain no iOS-specific code,
so they can be built and run with the host C compiler and validated here,
including against the real pinned Alpine rootfs archive when it has been
fetched by hermes/build/fetch-ish-source.sh.

This is the one part of the native iSH integration that can be exercised
end-to-end in a Linux CI/dev environment: the Objective-C kernel-boot and
PTY-bridging glue under ISHBridge/*.m requires an iOS toolchain and the
compiled upstream Linux-kernel-as-library target, neither of which is
available here (see BUILD.md)."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BRIDGE_DIR = ROOT / "ISHBridge"
HARNESS_SOURCE = ROOT / "hermes" / "tests" / "ish_bridge" / "ish_bridge_test_main.c"
PINNED_ROOTFS = ROOT / "hermes" / "build" / "external" / "ish" / "rootfs.tar.gz"


def _compiler() -> str:
    for candidate in (os.environ.get("CC"), "cc", "clang", "gcc"):
        if candidate and shutil.which(candidate):
            return candidate
    raise unittest.SkipTest("no C compiler available to build the ISHBridge test harness")


@unittest.skipUnless(shutil.which("cc") or shutil.which("gcc") or shutil.which("clang"),
                      "no C compiler available")
class IshBridgeCTests(unittest.TestCase):
    build_dir: Path
    binary: Path

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("pkg-config"):
            subprocess.run(["pkg-config", "--exists", "zlib"], check=False)
        # Never write scratch files under /tmp; use a directory under the
        # caller's home instead, cleaned up in tearDownClass.
        cls.build_dir = Path(tempfile.mkdtemp(prefix="ish-bridge-test-", dir=str(Path.home())))
        cls.binary = cls.build_dir / "ish_bridge_test"
        compile_command = [
            _compiler(), "-std=c11", "-O0", "-g",
            str(HARNESS_SOURCE),
            str(BRIDGE_DIR / "ish_path_safety.c"),
            str(BRIDGE_DIR / "ish_rootfs.c"),
            str(BRIDGE_DIR / "ish_exit_protocol.c"),
            "-lsqlite3", "-lz", "-o", str(cls.binary),
        ]
        result = subprocess.run(compile_command, capture_output=True, text=True)
        if result.returncode != 0:
            raise unittest.SkipTest(
                f"could not compile ISHBridge test harness (likely missing zlib headers): "
                f"{result.stderr}"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.build_dir, ignore_errors=True)

    def _run(self, *args: str, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(self.binary), *args], input=input_bytes, capture_output=True,
        )

    # ---- ish_path_safety ----

    def test_relative_entry_names_are_safe(self) -> None:
        result = self._run("path-safe", "etc/passwd")
        self.assertEqual(result.stdout.strip(), b"1")

    def test_parent_traversal_entry_names_are_rejected(self) -> None:
        for unsafe in ("../etc/passwd", "a/../../b", "a/..", ".."):
            with self.subTest(unsafe=unsafe):
                result = self._run("path-safe", unsafe)
                self.assertEqual(result.stdout.strip(), b"0")

    def test_absolute_entry_names_are_rejected(self) -> None:
        result = self._run("path-safe", "/etc/passwd")
        self.assertEqual(result.stdout.strip(), b"0")

    def test_empty_entry_name_is_rejected(self) -> None:
        result = self._run("path-safe", "")
        self.assertEqual(result.stdout.strip(), b"0")

    def test_safe_join_stays_within_root(self) -> None:
        result = self._run("path-join", "/root", "etc/passwd")
        self.assertEqual(result.stdout.strip(), b"/root/etc/passwd")

    def test_unsafe_join_is_refused(self) -> None:
        result = self._run("path-join", "/root", "../escape")
        self.assertEqual(result.stdout.strip(), b"UNSAFE")

    # ---- ish_rootfs extraction: security ----

    def _make_tarball(self, path: Path, members) -> None:
        import io

        with tarfile.open(path, "w:gz", format=tarfile.USTAR_FORMAT) as tar:
            for info, data in members:
                if data is None:
                    tar.addfile(info)
                else:
                    tar.addfile(info, io.BytesIO(data))

    def test_path_traversal_entry_is_rejected_without_writing_outside_root(self) -> None:
        archive = self.build_dir / "traversal.tar.gz"
        info = tarfile.TarInfo(name="../escaped.txt")
        info.size = 5
        self._make_tarball(archive, [(info, b"pwned")])
        dest = self.build_dir / "dest-traversal"
        dest.mkdir()
        result = self._run("extract", str(archive), str(dest))
        self.assertEqual(result.stdout.strip(), b"-4")
        self.assertFalse((self.build_dir / "escaped.txt").exists())
        self.assertEqual(list(dest.iterdir()), [])

    def test_absolute_path_entry_is_rejected(self) -> None:
        archive = self.build_dir / "absolute.tar.gz"
        info = tarfile.TarInfo(name="/etc/evil.txt")
        info.size = 5
        self._make_tarball(archive, [(info, b"pwned")])
        dest = self.build_dir / "dest-absolute"
        dest.mkdir()
        result = self._run("extract", str(archive), str(dest))
        self.assertEqual(result.stdout.strip(), b"-4")

    def test_symlink_escape_write_through_is_rejected(self) -> None:
        archive = self.build_dir / "symlink-escape.tar.gz"
        link = tarfile.TarInfo(name="escape")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc"
        through = tarfile.TarInfo(name="escape/evil.txt")
        through.size = 5
        self._make_tarball(archive, [(link, None), (through, b"pwned")])
        dest = self.build_dir / "dest-symlink"
        dest.mkdir()
        result = self._run("extract", str(archive), str(dest))
        # The dangling symlink object itself may be created (it is never
        # dereferenced by the host extractor), but writing *through* it must
        # fail rather than silently following it out of the sandboxed root.
        self.assertNotEqual(result.stdout.strip(), b"0")
        self.assertFalse(Path("/etc/evil.txt").exists())

    def test_well_formed_archive_extracts_successfully(self) -> None:
        archive = self.build_dir / "good.tar.gz"
        file_info = tarfile.TarInfo(name="a/b.txt")
        file_info.size = 5
        dir_info = tarfile.TarInfo(name="a/c")
        dir_info.type = tarfile.DIRTYPE
        link_info = tarfile.TarInfo(name="a/link.txt")
        link_info.type = tarfile.SYMTYPE
        link_info.linkname = "b.txt"
        self._make_tarball(archive, [(file_info, b"hello"), (dir_info, None), (link_info, None)])
        dest = self.build_dir / "dest-good"
        dest.mkdir()
        result = self._run("extract", str(archive), str(dest))
        self.assertEqual(result.stdout.strip(), b"0")
        self.assertEqual((dest / "a" / "b.txt").read_bytes(), b"hello")
        self.assertTrue((dest / "a" / "c").is_dir())
        self.assertTrue((dest / "a" / "link.txt").is_symlink())

    def test_read_only_directories_are_chmodded_after_their_contents_extract(self) -> None:
        archive = self.build_dir / "read-only-directories.tar.gz"
        outer = tarfile.TarInfo(name="root")
        outer.type = tarfile.DIRTYPE
        outer.mode = 0o555
        inner = tarfile.TarInfo(name="root/etc")
        inner.type = tarfile.DIRTYPE
        inner.mode = 0o500
        release = tarfile.TarInfo(name="root/etc/alpine-release")
        release.mode = 0o444
        data = b"3.21.3\n"
        release.size = len(data)
        self._make_tarball(archive, [(outer, None), (inner, None), (release, data)])
        dest = self.build_dir / "dest-read-only"
        dest.mkdir()

        result = self._run("extract", str(archive), str(dest))

        self.assertEqual(result.stdout.strip(), b"0", result.stderr)
        self.assertEqual((dest / "root/etc/alpine-release").read_bytes(), data)
        self.assertEqual(stat.S_IMODE((dest / "root").stat().st_mode), 0o555)
        self.assertEqual(stat.S_IMODE((dest / "root/etc").stat().st_mode), 0o500)

    def test_raw_rootfs_is_converted_to_iSH_fakefs_layout(self) -> None:
        import sqlite3

        root = self.build_dir / "fakefs-root"
        (root / "bin").mkdir(parents=True)
        (root / "etc").mkdir()
        (root / "bin/busybox").write_bytes(b"busybox")
        (root / "etc/alpine-release").write_text("3.21.3\n", encoding="utf-8")
        (root / "sbin").mkdir()
        (root / "sbin/init").symlink_to("../bin/busybox")
        os.chmod(root / "bin/busybox", 0o755)
        (root / "bin/sh").symlink_to("busybox")

        result = self._run("fakefsify", str(root))

        self.assertEqual(result.stdout.strip(), b"0", result.stderr)
        self.assertFalse((root / "bin").exists())
        self.assertTrue((root / "data/bin/busybox").is_file())
        self.assertFalse((root / "data/bin/sh").is_symlink())
        self.assertEqual((root / "data/bin/sh").read_text(encoding="utf-8"), "busybox")
        with sqlite3.connect(root / "meta.db") as db:
            paths = dict(db.execute("SELECT CAST(path AS TEXT), inode FROM paths"))
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 3)
            self.assertIn("", paths)
            self.assertIn("bin/busybox", paths)
            self.assertIn("etc/alpine-release", paths)
            mode_blob = db.execute(
                "SELECT stat FROM stats WHERE inode = ?", (paths["bin/sh"],)
            ).fetchone()[0]
            mode = int.from_bytes(mode_blob[:4], byteorder="little")
            self.assertTrue(stat.S_ISLNK(mode))

    def test_fakefs_conversion_is_idempotent(self) -> None:
        root = self.build_dir / "fakefs-idempotent"
        (root / "bin").mkdir(parents=True)
        (root / "etc").mkdir()
        (root / "bin/busybox").write_bytes(b"busybox")
        (root / "etc/alpine-release").write_text("3.21.3\n", encoding="utf-8")
        (root / "sbin").mkdir()
        (root / "sbin/init").symlink_to("../bin/busybox")
        os.chmod(root / "bin/busybox", 0o755)

        first = self._run("fakefsify", str(root))
        second = self._run("fakefsify", str(root))

        self.assertEqual(first.stdout.strip(), b"0", first.stderr)
        self.assertEqual(second.stdout.strip(), b"0", second.stderr)
        self.assertEqual((root / "data/bin/busybox").read_bytes(), b"busybox")

    def test_tar_dot_prefixes_are_normalized_for_fakefs_database_paths(self) -> None:
        import sqlite3

        archive = self.build_dir / "dot-prefix.tar.gz"
        busybox = tarfile.TarInfo(name="./bin/busybox")
        busybox.mode = 0o755
        busybox.size = 7
        release = tarfile.TarInfo(name="./etc/alpine-release")
        release.size = 7
        init = tarfile.TarInfo(name="./sbin/init")
        init.type = tarfile.SYMTYPE
        init.linkname = "../bin/busybox"
        self._make_tarball(archive, [
            (busybox, b"busybox"),
            (release, b"3.21.3\n"),
            (init, None),
        ])
        root = self.build_dir / "dot-prefix-root"
        root.mkdir()

        extracted = self._run("extract", str(archive), str(root))
        converted = self._run("fakefsify", str(root))

        self.assertEqual(extracted.stdout.strip(), b"0", extracted.stderr)
        self.assertEqual(converted.stdout.strip(), b"0", converted.stderr)
        with sqlite3.connect(root / "meta.db") as db:
            paths = {row[0] for row in db.execute("SELECT CAST(path AS TEXT) FROM paths")}
        self.assertIn("bin/busybox", paths)
        self.assertIn("etc/alpine-release", paths)
        self.assertIn("sbin/init", paths)
        self.assertNotIn("./bin/busybox", paths)

    # ---- ish_rootfs extraction: the real pinned archive ----

    @unittest.skipUnless(PINNED_ROOTFS.exists(), "pinned iSH rootfs has not been fetched")
    def test_pinned_alpine_rootfs_extracts_with_expected_markers(self) -> None:
        import sqlite3

        dest = self.build_dir / "dest-pinned"
        dest.mkdir()
        result = self._run("extract", str(PINNED_ROOTFS), str(dest))
        self.assertEqual(result.stdout.strip(), b"0", result.stderr)
        self.assertTrue((dest / "bin" / "busybox").exists())
        self.assertTrue((dest / "etc" / "alpine-release").exists())
        self.assertTrue((dest / "sbin" / "init").exists())
        converted = self._run("fakefsify", str(dest))
        self.assertEqual(converted.stdout.strip(), b"0", converted.stderr)
        self.assertTrue((dest / "data" / "bin" / "busybox").exists())
        self.assertTrue((dest / "data" / "etc" / "alpine-release").exists())
        self.assertTrue((dest / "data" / "sbin" / "init").exists())
        with sqlite3.connect(dest / "meta.db") as db:
            self.assertGreater(
                db.execute("SELECT count(*) FROM paths").fetchone()[0], 1000
            )

    # ---- ish_exit_protocol: wrap + streaming scan ----

    def test_wrap_registers_an_exit_trap_before_the_user_command(self) -> None:
        result = self._run("wrap", input_bytes=b"echo hi")
        script = result.stdout.decode()
        self.assertIn("trap 'printf \"\\035ISH-EXIT:%d\\035\" \"$?\"' EXIT", script)
        trap_index = script.index("trap ")
        command_index = script.index("echo hi")
        self.assertLess(trap_index, command_index)

    def _run_wrapped_through_shell(self, user_command: str, chunk_size: int) -> subprocess.CompletedProcess:
        wrap_result = self._run("wrap", input_bytes=user_command.encode())
        self.assertEqual(wrap_result.returncode, 0, wrap_result.stderr)
        shell_result = subprocess.run(
            ["sh"], input=wrap_result.stdout, capture_output=True,
        )
        return self._run("scan", str(chunk_size), input_bytes=shell_result.stdout)

    def test_scanner_recovers_zero_exit_status_and_strips_sentinel(self) -> None:
        result = self._run_wrapped_through_shell("echo ok", chunk_size=0)
        self.assertEqual(result.stdout, b"ok\n")
        self.assertIn(b"MATCHED 0", result.stderr)

    def test_scanner_recovers_status_from_a_failing_command(self) -> None:
        result = self._run_wrapped_through_shell("false", chunk_size=0)
        self.assertIn(b"MATCHED 1", result.stderr)

    def test_scanner_recovers_status_when_user_command_calls_exit_explicitly(self) -> None:
        # A bare trailing statement after the user command would never run
        # here (`exit` terminates the shell immediately); the EXIT trap is
        # what makes this reliable.
        result = self._run_wrapped_through_shell(
            "echo hello; echo world >&2; exit 7", chunk_size=0,
        )
        self.assertEqual(result.stdout, b"hello\n")
        self.assertIn(b"MATCHED 7", result.stderr)

    def test_scanner_still_matches_when_fed_one_byte_at_a_time(self) -> None:
        result = self._run_wrapped_through_shell(
            "echo chunked-test; exit 42", chunk_size=1,
        )
        self.assertEqual(result.stdout, b"chunked-test\n")
        self.assertIn(b"MATCHED 42", result.stderr)

    def test_exec_replacing_the_shell_is_a_documented_no_sentinel_case(self) -> None:
        # exec(1) replaces the shell process image outright; nothing we
        # register can run afterward. The native glue must treat a
        # hangup-without-sentinel as this known, documented case rather than
        # hanging forever (see ISHBridge/ish_kernel_bridge.m).
        result = self._run_wrapped_through_shell("exec true", chunk_size=0)
        self.assertIn(b"NOMATCH", result.stderr)

    def test_plain_output_without_any_sentinel_passes_through_unchanged(self) -> None:
        scanner_input = b"just some ordinary command output\nwith two lines\n"
        result = self._run("scan", "0", input_bytes=scanner_input)
        self.assertEqual(result.stdout, scanner_input)
        self.assertIn(b"NOMATCH", result.stderr)


if __name__ == "__main__":
    unittest.main()
