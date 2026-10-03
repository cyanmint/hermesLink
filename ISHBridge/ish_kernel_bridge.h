/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#ifndef ISH_KERNEL_BRIDGE_H
#define ISH_KERNEL_BRIDGE_H

#ifdef __cplusplus
extern "C" {
#endif

/* Public entry points exported by Ish.framework and consumed by
 * Blink/Commands/ish.m. This header intentionally has no Foundation/UIKit
 * dependency so it can be included from plain C callers too.
 *
 * Design (see BUILD.md and ISHBridge/ish_kernel_bridge.m for the full
 * rationale): the pinned upstream iSH Linux kernel
 * (hermes/build/external/ish/source, built by hermes/build/build-ish-static.sh
 * into libraries this target links against) is booted exactly once per app
 * process via `actuate_kernel()`, on a dedicated background thread, because
 * upstream's `run_kernel()` never returns. Every `ish <command>` invocation
 * afterward reuses that same already-booted guest (and its persistent,
 * on-disk Alpine root) by calling upstream's `linux_start_session()` for a
 * single `/bin/sh -c <command>` guest process, bridging its pty to the
 * calling ios_system command's stdio. */

typedef enum {
  ISH_RUN_OK = 0,
  ISH_RUN_ERR_INVALID_ARGUMENT = -1,
  ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED = -2,
  ISH_RUN_ERR_BOOT_TIMEOUT = -3,
  ISH_RUN_ERR_SESSION_START_FAILED = -4,
  /* The guest session ended without emitting the exit-status sentinel,
   * usually because the command replaced the shell via exec(2). */
  ISH_RUN_ERR_NO_EXIT_SENTINEL = -5,
  /* This build was compiled without the native guest kernel bridge linked
   * in (ISH_NATIVE_AVAILABLE=NO in hermes/build/ISHNative.xcconfig — the
   * default, since the prebuilt static libraries
   * hermes/build/build-ish-static.sh produces are not part of a plain
   * checkout). See ISHBridge/ish_kernel_bridge_stub.m. */
  ISH_RUN_ERR_NOT_AVAILABLE = -6,
  ISH_RUN_ERR_KERNEL_PANIC = -7,
  ISH_RUN_ERR_MOUNT_FAILED = -8,
} ish_run_status;

typedef void (*ish_log_handler)(const char *message);

/* Configures the persistent guest-root directory and optional diagnostic
 * callback. HermesLink supplies a profile below Files-visible Documents/iSH.
 * Call before the first boot; repeated calls with the same values are harmless. */
int ish_configure(const char *root_path, ish_log_handler log_handler);

/* Extracts a gzip-compressed ustar rootfs archive into a new destination
 * directory and verifies its Alpine rootfs markers. */
int ish_import_rootfs_archive(const char *archive_path, const char *dest_root);

/* Boots the shared guest kernel if it has not been booted yet in this app
 * process (idempotent and thread-safe; cheap to call before every `ish`
 * invocation). Returns ISH_RUN_OK once ready to accept ish_run_command()
 * calls, or a negative ish_run_status if first-time rootfs preparation
 * failed. Does not block for the lifetime of the kernel — only for the
 * one-time setup — because the boot itself runs on its own permanent
 * background thread. */
int ish_kernel_ensure_booted(void);
int ish_kernel_has_booted(void);

/* Mounts the app's Files-visible Documents directory at an existing guest
 * directory. On ISH_RUN_ERR_MOUNT_FAILED, mount_error_out receives the
 * negative iSH errno for the failed mount. */
int ish_mount_documents(const char *mount_path, int *mount_error_out);

/* Runs `command` to completion as `/bin/sh -c <command>` inside the
 * persistent guest, bridging the guest pty to `input_fd`/`output_fd`
 * (plain file descriptors, e.g. from ios_system's thread_stdin/thread_stdout
 * via fileno(3); -1 for `input_fd` leaves guest stdin at EOF). `cols`/`rows`
 * set the initial pty window size (0 to skip). On ISH_RUN_OK,
 * `*exit_code_out` holds the guest command's real exit status (0-255).
 * On ISH_RUN_ERR_SESSION_START_FAILED, `*session_error_out` holds the
 * negative upstream error returned while creating the session. */
int ish_run_command(const char *command, int input_fd, int output_fd, int cols, int rows,
                    int *exit_code_out, int *session_error_out);

#ifdef __cplusplus
}
#endif

#endif /* ISH_KERNEL_BRIDGE_H */
