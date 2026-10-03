/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#include "ish_kernel_bridge.h"

#include <stdio.h>

/* Default implementation compiled into the Blink target when the
 * prebuilt Ish.framework is unavailable (ISH_NATIVE_AVAILABLE defaults to
 * NO). Rather than make the
 * whole app fail to link without them, this stub keeps the `ish` native
 * command (Blink/Commands/ish.m) and Hermes Agent tool
 * (hermes/overlay/hermes/tools/ish_tool.py) registered and working end to
 * end everywhere else, reporting a clear "not available in this build"
 * status instead of silently doing nothing or crashing.
 *
 * This stub provides the same API as Ish.framework so the native command
 * can remain registered in builds that do not have the iSH runtime. */

int ish_configure(const char *root_path, ish_log_handler log_handler) {
  (void) root_path;
  (void) log_handler;
  return ISH_RUN_OK;
}

int ish_configure_documents(const char *host_path, const char *guest_mount_path,
                            unsigned int mask) {
  (void) host_path;
  (void) guest_mount_path;
  (void) mask;
  return ISH_RUN_OK;
}

int ish_documents_configuration_is_current(const char *host_path,
                                           const char *guest_mount_path,
                                           unsigned int mask) {
  (void) host_path;
  (void) guest_mount_path;
  (void) mask;
  return 1;
}

int ish_kernel_ensure_booted(void) {
  return ISH_RUN_ERR_NOT_AVAILABLE;
}

int ish_kernel_has_booted(void) {
  return 0;
}

int ish_import_rootfs_archive(const char *archive_path, const char *dest_root) {
  (void) archive_path;
  (void) dest_root;
  return ISH_RUN_ERR_NOT_AVAILABLE;
}

int ish_run_command(const char *command, int input_fd, int output_fd, int cols, int rows,
                    int *exit_code_out, int *session_error_out) {
  (void) command;
  (void) input_fd;
  (void) output_fd;
  (void) cols;
  (void) rows;
  if (exit_code_out != NULL) {
    *exit_code_out = 0;
  }
  if (session_error_out != NULL) {
    *session_error_out = 0;
  }
  return ISH_RUN_ERR_NOT_AVAILABLE;
}
