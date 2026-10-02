#!/usr/bin/env python3
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Verify the exact upstream iSH source snapshot and Alpine rootfs inputs."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tarfile
from pathlib import Path


ISH_COMMIT = "83348361fe65311f6e87ad2e1cbb0ac38d123f69"
ISH_SOURCE_SHA256 = "db1ada190091668479f3cc060ceb69a392c44460326bbb2446699320820d5819"
ROOTFS_URL = (
    "https://github.com/ish-app/roots/releases/download/"
    "g00712ff0a54b2839c5aa1a8ed758003ca65357dc/appstore-apk.tar.gz"
)
ROOTFS_SHA256 = "776b16416894e5a8bec220b8d4726c46bb993289e8e48fdac54a519396e40a93"
ROOTFS_REQUIRED_PATHS = {"bin/busybox", "etc/alpine-release", "sbin/init"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha256(actual: str, expected: str, description: str) -> None:
    if actual != expected:
        raise ValueError(
            f"{description} SHA-256 mismatch: expected {expected}, got {actual}"
        )


def _archive_sha256(source: Path) -> str:
    process = subprocess.Popen(
        ["git", "-C", str(source), "archive", "--format=tar", ISH_COMMIT],
        stdout=subprocess.PIPE,
    )
    assert process.stdout is not None
    digest = hashlib.sha256()
    for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
        digest.update(chunk)
    process.stdout.close()
    if process.wait() != 0:
        raise ValueError(f"could not create the pinned iSH source archive: {source}")
    return digest.hexdigest()


def verify_source(source: Path) -> None:
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"not a usable iSH git checkout: {source}") from error
    if commit != ISH_COMMIT:
        raise ValueError(f"iSH source commit mismatch: expected {ISH_COMMIT}, got {commit}")
    require_sha256(_archive_sha256(source), ISH_SOURCE_SHA256, "iSH source")

    try:
        changes = subprocess.check_output(
            [
                "git",
                "-C",
                str(source),
                "status",
                "--porcelain",
                "--ignore-submodules=none",
            ],
            text=True,
        )
        status = subprocess.check_output(
            ["git", "-C", str(source), "submodule", "status", "--recursive"],
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"could not inspect pinned iSH submodules: {source}") from error
    if changes.strip():
        raise ValueError(
            f"iSH source or submodules have local modifications: {source}\n{changes}"
        )
    if any(line and line[0] != " " for line in status.splitlines()):
        raise ValueError("iSH submodules are uninitialized or differ from pinned revisions")


def verify_rootfs(rootfs: Path) -> None:
    try:
        require_sha256(sha256_file(rootfs), ROOTFS_SHA256, "iSH Alpine rootfs")
        with tarfile.open(rootfs, mode="r:gz") as archive:
            paths = {
                member.name.removeprefix("./").rstrip("/")
                for member in archive.getmembers()
            }
    except (OSError, tarfile.TarError) as error:
        raise ValueError(f"invalid iSH Alpine rootfs archive: {rootfs}") from error
    missing = ROOTFS_REQUIRED_PATHS - paths
    if missing:
        raise ValueError(f"iSH Alpine rootfs is missing expected files: {sorted(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--rootfs", type=Path)
    args = parser.parse_args()
    if args.source is None and args.rootfs is None:
        parser.error("provide --source, --rootfs, or both")
    try:
        if args.source is not None:
            verify_source(args.source)
        if args.rootfs is not None:
            verify_rootfs(args.rootfs)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    if args.source is not None:
        print(f"Verified iSH {ISH_COMMIT} (source archive sha256 {ISH_SOURCE_SHA256}).")
    if args.rootfs is not None:
        print(f"Verified pinned Alpine rootfs (sha256 {ROOTFS_SHA256}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
