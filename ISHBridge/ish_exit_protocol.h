/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#ifndef ISH_EXIT_PROTOCOL_H
#define ISH_EXIT_PROTOCOL_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* iSH's own `linux_start_session()` (see the pinned upstream
 * app/LinuxInterop.h / app/LinuxInterop.c) only reports that a guest
 * process has started executing — it has no "this guest command has
 * exited with this status" callback, because upstream's own GUI never
 * needed one (interactive sessions are torn down by the user, or by the
 * pty hanging up when all references to it close; see the ios_pty_cleanup
 * EPOLLHUP path in the pinned app/LinuxPTY.c). A non-interactive
 * `ish <command>` invocation needs a real, trustworthy exit status to
 * return to the calling shell (so `$?` works), so this glue wraps every
 * guest command in a trailer that prints a short, hard-to-collide binary
 * sentinel carrying the shell exit status once the command finishes, and
 * implements a streaming scanner that strips the sentinel back out of the
 * guest's PTY output before it reaches the user's terminal.
 *
 * This is original protocol/implementation; no upstream iSH source is
 * reused. */

/* ASCII Group Separator (0x1D) is vanishingly unlikely to appear in normal
 * terminal output, and is not interpreted by common terminal emulators. */
#define ISH_EXIT_SENTINEL_MARKER 0x1D
#define ISH_EXIT_SENTINEL_TAG "ISH-EXIT:"

/* Builds the `/bin/sh -c`-ready script that runs `user_command` and then
 * emits the exit sentinel for its real exit status. Returns the number of
 * bytes that would be written (as snprintf does), or a negative number if
 * `user_command` is NULL. Truncation (return value >= out_size) must be
 * treated by the caller as an error: never execute a truncated script. */
int ish_exit_protocol_wrap_command(const char *user_command, char *out, size_t out_size);

typedef struct {
  unsigned char pending[32];
  size_t pending_len;
  int have_prefix;    /* 1 once the full literal sentinel prefix has matched */
  int digits_seen;
  int exit_code;
  int matched;         /* 1 once a complete, well-formed sentinel has been consumed */
} ish_exit_scanner;

void ish_exit_scanner_init(ish_exit_scanner *scanner);

/* Feeds `len` bytes of freshly-received guest output through the scanner.
 * Bytes that are not part of a recognized sentinel are forwarded via
 * `emit(ctx, data, len)` immediately (so interactive output is not delayed
 * beyond what it takes to rule out a sentinel match); sentinel bytes are
 * consumed and never forwarded. Safe to call repeatedly, including after a
 * match (scanner->matched stays 1 and further bytes are forwarded as-is).
 * Returns 0 on success; returns -1 only if `scanner`, `data" (with len>0) or
 * `emit` is NULL. */
int ish_exit_scanner_feed(ish_exit_scanner *scanner, const unsigned char *data, size_t len,
                           void (*emit)(void *ctx, const unsigned char *data, size_t len), void *ctx);

#ifdef __cplusplus
}
#endif

#endif /* ISH_EXIT_PROTOCOL_H */
