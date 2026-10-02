/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#ifndef ISH_ROOTFS_H
#define ISH_ROOTFS_H

#ifdef __cplusplus
extern "C" {
#endif

/* Safe, from-scratch gzip+ustar extraction of the pinned Alpine rootfs
 * archive into writable, persistent app storage. This is original glue
 * code: it does not reuse or copy any part of upstream iSH's own root
 * import pipeline (app/Roots.m, which is UIKit-coupled and not vendored
 * here). It links against zlib only (a standard iOS system library) for
 * gzip framing, and parses the plain POSIX ustar container format used by
 * the pinned `rootfs.tar.gz` (regular files, directories and symlinks —
 * the only entry types present in that pinned archive; see
 * hermes/tests/test_ish_rootfs_extract.py for a format audit against the
 * real pinned asset).
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

#ifdef __cplusplus
}
#endif

#endif /* ISH_ROOTFS_H */
