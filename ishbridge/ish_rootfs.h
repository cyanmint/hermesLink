/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#ifndef ISH_ROOTFS_H
#define ISH_ROOTFS_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Safe, from-scratch gzip+ustar extraction of the pinned Alpine rootfs
 * archive into writable, persistent app storage, followed by creation of
 * the SQLite metadata required by upstream fakefs. This is original glue
 * code: it does not reuse or copy any part of upstream iSH's own root
 * import pipeline (app/Roots.m, which is UIKit-coupled and not vendored
 * here). It uses the standard iOS zlib and SQLite libraries and parses
 * the plain POSIX ustar container format (regular files, directories and
 * symlinks — the only entry types present in the pinned archive; see
 * tests/hermes/test_ish_bridge_c.py for host-side coverage).
 *
 * Security properties:
 *  - every entry path is validated with ish_path_is_safe_entry_name()
 *    before touching the filesystem (rejects absolute paths and ".."
 *    components — CWE-22 path traversal);
 *  - directories are created component-by-component; if an intermediate
 *    component already exists and is not a directory (in particular, is a
 *    symlink), extraction of that entry is aborted instead of following or
 *    replacing it (avoids a symlink-race escape of the destination root);
 *  - unsupported entry types (device nodes, FIFOs, hard links, GNU
 *    long-name extensions) cause a hard error rather than being silently
 *    mis-parsed. */

typedef enum {
  ISH_ROOTFS_OK = 0,
  ISH_ROOTFS_ERR_OPEN = -1,
  ISH_ROOTFS_ERR_READ = -2,
  ISH_ROOTFS_ERR_FORMAT = -3,
  ISH_ROOTFS_ERR_UNSAFE_PATH = -4,
  ISH_ROOTFS_ERR_UNSUPPORTED_TYPE = -5,
  ISH_ROOTFS_ERR_IO = -6,
  ISH_ROOTFS_ERR_DEST = -7,
} ish_rootfs_status;

/* Extracts the gzip-compressed ustar archive at `archive_path` into
 * `dest_root`, which must already exist (or be creatable with mkdir(2) by
 * the caller) and be writable. Returns ISH_ROOTFS_OK on success, or a
 * negative ish_rootfs_status. On any error, already-written files are left
 * in place (extraction is not transactional); callers extracting into a
 * fresh, uniquely-named staging directory can discard it on failure before
 * publishing. */
int ish_rootfs_extract(const char *archive_path, const char *dest_root);

/* Converts an extracted, ordinary root tree in `root` to the pinned iSH
 * fakefs layout (`root/data` plus `root/meta.db`). Existing fakefs profiles
 * are validated and left unchanged. The tree must contain executable
 * `bin/busybox`, `etc/alpine-release`, and `sbin/init` entries. */
int ish_rootfs_prepare_fakefs(const char *root);

/* Writes an executable guest-side Documents mount helper into a prepared
 * fakefs root and indexes it in meta.db. */
int ish_rootfs_write_documents_mount_script(const char *root,
                                            const char *host_documents_path);

/* Creates and indexes the resolver file before the guest kernel starts, then
 * updates its host-backed contents without using guest-kernel file APIs. */
int ish_rootfs_prepare_resolv_conf(const char *root);
int ish_rootfs_update_resolv_conf(const char *root, const char *contents,
                                  size_t length);

#ifdef __cplusplus
}
#endif

#endif /* ISH_ROOTFS_H */
