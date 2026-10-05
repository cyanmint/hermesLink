/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#ifndef ISH_PATH_SAFETY_H
#define ISH_PATH_SAFETY_H

#ifdef __cplusplus
extern "C" {
#endif

/* Pure, host-independent path validation used before any filesystem write
 * while extracting the pinned Alpine rootfs archive into persistent app
 * storage. No upstream iSH source is used here; this is original glue that
 * guards against path traversal (CWE-22) and symlink-based escape of the
 * extraction root. */

/* Returns 1 if `entry_name` (a tar member path, '/'-separated, NOT yet
 * joined to a destination root) is safe to extract: non-empty, relative
 * (does not start with '/'), contains no ".." path component, and contains
 * no embedded NUL. Returns 0 otherwise. */
int ish_path_is_safe_entry_name(const char *entry_name);

/* Returns 1 if `link_target` is an acceptable symlink target to materialize
 * verbatim on the host filesystem: non-empty and free of embedded NUL.
 * Absolute and ".."-relative symlink targets ARE allowed to be recorded
 * (they describe the guest's view of its own root and are never resolved
 * by the host extractor itself), but callers must still use
 * ish_path_is_safe_entry_name() on the symlink's own path and must create
 * the link with a non-dereferencing primitive (e.g. symlink(2)), never by
 * opening through intermediate components that could themselves be
 * symlinks. */
int ish_path_is_safe_link_target(const char *link_target);

/* Joins `root` and `relative` into `out` (size `out_size`), rejecting the
 * join (returns 0) if the result would not remain lexically within `root`
 * (defense in depth on top of ish_path_is_safe_entry_name) or would not fit
 * in the buffer. Returns 1 and NUL-terminates `out` on success. */
int ish_path_join_within_root(const char *root, const char *relative, char *out, unsigned long out_size);

#ifdef __cplusplus
}
#endif

#endif /* ISH_PATH_SAFETY_H */
