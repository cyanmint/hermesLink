/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#import <Foundation/Foundation.h>
#import "ISHRootfsProfiles.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <termios.h>
#include <unistd.h>

#include "ios_error.h"
#include "ish_kernel_bridge.h"

/* Blink/Commands/hermes.m exports this diagnostics logger. */
extern void HermesLinkAppendLog(const char *message);

/* Registered as the native `ish` shell command (Resources/blinkCommandsDictionary.plist),
 * i.e. `ish <command...>` — not a Blink-side `ish container` subcommand. See
 * BUILD.md for the overall design: a single, shared iSH Linux kernel +
 * persistent Alpine guest root is booted once per app process
 * (ISHBridge/ish_kernel_bridge.m), and every `ish` invocation runs its
 * command inside that already-booted guest, bridging the guest pty to this
 * ios_system command's own stdio so it behaves like any other Blink shell
 * command (correct $?, live interactive I/O, Ctrl-C/Ctrl-D passthrough via
 * the normal ios_system signal/EOF path on thread_stdin). */
__attribute__((visibility("default")))
int ish_main(int argc, char *argv[]) {
  NSError *profileError = nil;
  NSString *ishRoot = ISHRootfsActiveProfilePath(&profileError);
  if (ishRoot == nil) {
    fprintf(thread_stderr, "ish: could not prepare rootfs profiles: %s\n",
            profileError.localizedDescription.UTF8String ?: "unknown filesystem error");
    return 71;
  }
  if (ish_configure(ishRoot.fileSystemRepresentation, HermesLinkAppendLog) != ISH_RUN_OK) {
    fprintf(thread_stderr, "ish: rootfs profile changed after the kernel started; force-quit and relaunch the app\n");
    return 70;
  }
  NSString *documentsPath = ISHDocumentsAutoMountEnabled()
      ? ISHDocumentsHostPath() : @"";
  if (ish_configure_documents(documentsPath.UTF8String,
                              ISHDocumentsGuestMountPath().UTF8String,
                              (unsigned int) ISHDocumentsMountMask()) != ISH_RUN_OK) {
    fprintf(thread_stderr, "ish: invalid Documents mount settings\n");
    return 70;
  }

  NSMutableString *command = [NSMutableString new];
  if (argc < 2) {
    [command appendString:@"/bin/sh"];
  } else {
    for (int i = 1; i < argc; i++) {
      if (i > 1) {
        [command appendString:@" "];
      }
      [command appendString:[NSString stringWithUTF8String:argv[i]]];
    }
  }

  int input_fd = thread_stdin != NULL ? fileno(thread_stdin) : -1;
  int output_fd = thread_stdout != NULL ? fileno(thread_stdout) : -1;

  int cols = 80;
  int rows = 24;
  struct winsize ws;
  if (input_fd >= 0 && ioctl(input_fd, TIOCGWINSZ, &ws) == 0 && ws.ws_col > 0 && ws.ws_row > 0) {
    cols = ws.ws_col;
    rows = ws.ws_row;
  }

  int exit_code = 0;
  int session_error = 0;
  int status = ish_run_command(command.UTF8String, input_fd, output_fd, cols, rows,
                               &exit_code, &session_error);
  switch (status) {
    case ISH_RUN_OK:
      return exit_code;
    case ISH_RUN_ERR_INVALID_ARGUMENT:
      fprintf(thread_stderr, "ish: invalid command\n");
      return 2;
    case ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED: {
      NSString *activeProfile = ISHRootfsActiveProfileName(NULL) ?: @"unknown";
      fprintf(thread_stderr,
              "ish: the selected rootfs profile '%s' is unusable. Remove it with "
              "`ishfs delete '%s' --yes`, then recreate it or import a valid rootfs. "
              "If it is the only profile, deletion resets it; force-quit and reopen Blink before retrying.\n",
              activeProfile.UTF8String,
              activeProfile.UTF8String);
      return 71;
    }
    case ISH_RUN_ERR_BOOT_TIMEOUT:
      fprintf(thread_stderr, "ish: the guest Linux kernel did not finish booting in time; try again\n");
      return 75;
    case ISH_RUN_ERR_KERNEL_PANIC:
      fprintf(thread_stderr, "ish: the guest Linux kernel panicked during startup (see diagnostics log)\n");
      return 70;
    case ISH_RUN_ERR_SESSION_START_FAILED:
      fprintf(thread_stderr, "ish: failed to start a guest session (upstream error %d; see diagnostics log)\n",
              session_error);
      return 71;
    case ISH_RUN_ERR_NOT_AVAILABLE:
      fprintf(thread_stderr,
              "ish: this build does not include the native Linux guest kernel "
              "(see BUILD.md's iSH integration status)\n");
      return 69;
    case ISH_RUN_ERR_NO_EXIT_SENTINEL:
      /* The guest session ended without reporting a status — most commonly
       * because its last action replaced the shell via exec(2). We cannot
       * recover the real status in that case (see
       * ISHBridge/ish_exit_protocol.h); report success rather than an
       * arbitrary, possibly-misleading failure code. */
      HermesLinkAppendLog("ish: guest session ended without an exit status (command likely used exec)");
      return 0;
    default:
      fprintf(thread_stderr, "ish: unexpected internal error (%d)\n", status);
      return 70;
  }
}
