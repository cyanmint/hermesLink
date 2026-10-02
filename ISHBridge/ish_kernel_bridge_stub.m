/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#include "ish_kernel_bridge.h"

#include <stdio.h>

/* Default implementation compiled into the Blink target (see
 * hermes/build/ISHNative.xcconfig: ISH_NATIVE_AVAILABLE defaults to NO).
 *
 * The real guest-kernel bridge (ish_kernel_bridge.m) requires linking the
 * prebuilt static libraries hermes/build/build-ish-static.sh produces from
 * the pinned upstream iSH Linux-kernel-as-library target — artifacts that
 * do not exist in a plain checkout and that this sandbox's CI cannot
 * build or verify (no Xcode/Meson; see BUILD.md). Rather than make the
 * whole app fail to link without them, this stub keeps the `ish` native
 * command (Blink/Commands/ish.m) and Hermes Agent tool
 * (hermes/overlay/hermes/tools/ish_tool.py) registered and working end to
 * end everywhere else, reporting a clear "not available in this build"
 * status instead of silently doing nothing or crashing.
 *
 * Exactly one of this file or ish_kernel_bridge.m is ever compiled, never
 * both (see EXCLUDED_SOURCE_FILE_NAMES in hermes/build/ISHNative.xcconfig),
 * so this file does not implement the terminal or root-path ABI.
 * at all — nothing in this build configuration calls into the pinned
 * kernel sources that declare it. */

int ish_kernel_ensure_booted(void) {
  return ISH_RUN_ERR_NOT_AVAILABLE;
}

int ish_run_command(const char *command, int input_fd, int output_fd, int cols, int rows, int *exit_code_out) {
  (void) command;
  (void) input_fd;
  (void) output_fd;
  (void) cols;
  (void) rows;
  if (exit_code_out != NULL) {
    *exit_code_out = 0;
  }
  return ISH_RUN_ERR_NOT_AVAILABLE;
}
