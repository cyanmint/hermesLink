# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Focused tests for pinned iSH source and rootfs acquisition."""

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFY_PATH = ROOT / "scripts" / "hermes" / "build" / "verify-ish-source.py"
SPEC = importlib.util.spec_from_file_location("verify_ish_source", VERIFY_PATH)
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class IshSourceTests(unittest.TestCase):
    def test_upstream_source_and_rootfs_are_immutable_pins(self):
        self.assertEqual(
            verify.ISH_COMMIT, "83348361fe65311f6e87ad2e1cbb0ac38d123f69"
        )
        self.assertEqual(
            verify.ISH_SOURCE_SHA256,
            "db1ada190091668479f3cc060ceb69a392c44460326bbb2446699320820d5819",
        )
        self.assertEqual(
            verify.ROOTFS_SHA256,
            "776b16416894e5a8bec220b8d4726c46bb993289e8e48fdac54a519396e40a93",
        )
        self.assertIn("g00712ff0a54b2839c5aa1a8ed758003ca65357dc", verify.ROOTFS_URL)

    def test_digest_verification_rejects_changed_bytes(self):
        digest = verify.sha256_bytes(b"pinned source")
        verify.require_sha256(digest, digest, "fixture")
        with self.assertRaisesRegex(ValueError, "fixture SHA-256 mismatch"):
            verify.require_sha256(digest, "0" * 64, "fixture")

    def test_source_script_uses_the_iSH_submodule_and_fetches_only_the_rootfs_asset(self):
        script = (ROOT / "scripts" / "hermes" / "build" / "fetch-ish-source.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("modules/ish", script)
        self.assertIn(verify.ROOTFS_URL, script)
        self.assertNotIn("submodule update", script)
        self.assertIn('python3 "$VERIFY" --source "$ISH_MODULE_SOURCE" --rootfs "$ROOTFS"', script)
        self.assertIn('MODE=rootfs-only', script)
        self.assertIn('if [ "$MODE" = all ]; then', script)
        self.assertNotRegex(script, r"\bgit\s+(?:clone|fetch)\b")
        self.assertIn("build-time inputs only", script)

    def test_rootfs_marker_set_matches_the_pinned_alpine_layout(self):
        self.assertEqual(
            verify.ROOTFS_REQUIRED_PATHS,
            {"bin/busybox", "etc/alpine-release", "sbin/init"},
        )

    def test_cached_upstream_inputs_pass_full_integrity_checks(self):
        source = ROOT / "hermes" / "build" / "external" / "ish" / "source"
        rootfs = ROOT / "hermes" / "build" / "external" / "ish" / "rootfs.tar.gz"
        if not source.exists() or not rootfs.exists():
            self.skipTest("pinned iSH build-time inputs have not been fetched")
        verify.verify_source(source)
        verify.verify_rootfs(rootfs)


if __name__ == "__main__":
    unittest.main()
