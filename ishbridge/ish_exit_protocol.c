/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#include "ish_exit_protocol.h"

#include <stdio.h>

#define ISH_PREFIX_TAIL_LEN 9 /* strlen(ISH_EXIT_SENTINEL_TAG) */
#define ISH_PREFIX_TOTAL_LEN (1 + ISH_PREFIX_TAIL_LEN) /* marker byte + tag */

_Static_assert(sizeof(ISH_EXIT_SENTINEL_TAG) - 1 == ISH_PREFIX_TAIL_LEN,
               "ISH_EXIT_SENTINEL_TAG length must match ISH_PREFIX_TAIL_LEN");
/* 0x1D (ASCII Group Separator) must match the octal \035 escape used in the
 * guest-side printf trailer built by ish_exit_protocol_wrap_command(). */
_Static_assert(ISH_EXIT_SENTINEL_MARKER == 035, "sentinel marker must be octal 035 (0x1D)");

int ish_exit_protocol_wrap_command(const char *user_command, char *out, size_t out_size) {
  if (user_command == NULL) {
    return -1;
  }
  /* The trap is registered BEFORE the user command runs so it still fires
   * if that command calls exit(2)/`exit` itself, or simply returns a
   * non-zero status: an EXIT trap always runs when the shell is about to
   * terminate (whether by falling off the end, `exit`, or most signals),
   * with "$?" already holding the real final status at that point — unlike
   * a plain trailing statement, which `exit` would skip entirely. The one
   * unavoidable exception is the user command replacing the shell via
   * `exec`: that genuinely replaces the process image, so nothing — ours
   * or otherwise — runs afterward; this mirrors ordinary shell semantics.
   * The sentinel itself is emitted by the guest's own /bin/sh via a
   * literal octal escape (\035), not interpolated from our marker macro, so
   * the two static_asserts above are what keeps them in lockstep. */
  return snprintf(out, out_size,
                   "trap 'printf \"\\035" ISH_EXIT_SENTINEL_TAG "%%d\\035\" \"$?\"' EXIT\n%s\n",
                   user_command);
}

void ish_exit_scanner_init(ish_exit_scanner *scanner) {
  if (scanner == NULL) {
    return;
  }
  scanner->pending_len = 0;
  scanner->have_prefix = 0;
  scanner->digits_seen = 0;
  scanner->exit_code = 0;
  scanner->matched = 0;
}

static const char ISH_PREFIX_TAIL[ISH_PREFIX_TAIL_LEN] = ISH_EXIT_SENTINEL_TAG;

static void ish_flush_pending(ish_exit_scanner *scanner,
                               void (*emit)(void *ctx, const unsigned char *data, size_t len), void *ctx) {
  if (scanner->pending_len > 0) {
    emit(ctx, scanner->pending, scanner->pending_len);
  }
  scanner->pending_len = 0;
  scanner->have_prefix = 0;
  scanner->digits_seen = 0;
  scanner->exit_code = 0;
}

static void ish_process_one_byte(ish_exit_scanner *scanner, unsigned char byte,
                                  void (*emit)(void *ctx, const unsigned char *data, size_t len), void *ctx) {
  if (scanner->matched) {
    emit(ctx, &byte, 1);
    return;
  }
  for (;;) {
    if (scanner->pending_len == 0) {
      if (byte == ISH_EXIT_SENTINEL_MARKER) {
        scanner->pending[0] = byte;
        scanner->pending_len = 1;
      } else {
        emit(ctx, &byte, 1);
      }
      return;
    }

    if (scanner->pending_len < ISH_PREFIX_TOTAL_LEN) {
      unsigned char expected = (unsigned char) ISH_PREFIX_TAIL[scanner->pending_len - 1];
      if (byte == expected) {
        scanner->pending[scanner->pending_len++] = byte;
        if (scanner->pending_len == ISH_PREFIX_TOTAL_LEN) {
          scanner->have_prefix = 1;
        }
        return;
      }
      /* Not our sentinel after all: release the buffered bytes verbatim and
       * re-evaluate this same byte from a clean state (it may itself begin
       * a fresh candidate, e.g. two adjacent 0x1D bytes in real output). */
      ish_flush_pending(scanner, emit, ctx);
      continue;
    }

    /* Prefix fully matched; now collect 1-3 decimal digits then the
     * closing marker byte. */
    if (byte >= '0' && byte <= '9' && scanner->digits_seen < 3) {
      if (scanner->pending_len < sizeof(scanner->pending)) {
        scanner->pending[scanner->pending_len++] = byte;
      }
      scanner->exit_code = scanner->exit_code * 10 + (byte - '0');
      scanner->digits_seen++;
      return;
    }
    if (byte == ISH_EXIT_SENTINEL_MARKER && scanner->digits_seen >= 1) {
      int code = scanner->exit_code;
      if (code < 0) {
        code = 0;
      }
      if (code > 255) {
        code = 255;
      }
      scanner->exit_code = code;
      scanner->matched = 1;
      scanner->pending_len = 0;
      scanner->have_prefix = 0;
      scanner->digits_seen = 0;
      return; /* entire sentinel consumed; nothing forwarded downstream */
    }
    /* Malformed: looked like a sentinel but is not one. Release everything
     * buffered so far, including this byte, as ordinary output. */
    if (scanner->pending_len < sizeof(scanner->pending)) {
      scanner->pending[scanner->pending_len++] = byte;
      ish_flush_pending(scanner, emit, ctx);
    } else {
      ish_flush_pending(scanner, emit, ctx);
      emit(ctx, &byte, 1);
    }
    return;
  }
}

int ish_exit_scanner_feed(ish_exit_scanner *scanner, const unsigned char *data, size_t len,
                           void (*emit)(void *ctx, const unsigned char *data, size_t len), void *ctx) {
  if (scanner == NULL || emit == NULL || (data == NULL && len > 0)) {
    return -1;
  }
  for (size_t i = 0; i < len; i++) {
    ish_process_one_byte(scanner, data[i], emit, ctx);
  }
  return 0;
}
