/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright.
 *
 * Small CLI test harness that exercises the portable (non-iOS-specific)
 * ISHBridge modules directly, so tests/hermes/test_ish_bridge_c.py can
 * validate the real glue logic — rootfs path-traversal defenses and the
 * guest exit-status sentinel protocol — without an iOS toolchain. This
 * harness itself is test infrastructure, not part of the shipped app. */
#include "../../../ishbridge/ish_path_safety.h"
#include "../../../ishbridge/ish_rootfs.h"
#include "../../../ishbridge/ish_exit_protocol.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int read_all_stdin(unsigned char **out_data, size_t *out_len) {
  size_t capacity = 65536;
  size_t len = 0;
  unsigned char *buffer = malloc(capacity);
  if (buffer == NULL) {
    return -1;
  }
  for (;;) {
    if (len == capacity) {
      capacity *= 2;
      unsigned char *grown = realloc(buffer, capacity);
      if (grown == NULL) {
        free(buffer);
        return -1;
      }
      buffer = grown;
    }
    ssize_t got = read(0, buffer + len, capacity - len);
    if (got < 0) {
      free(buffer);
      return -1;
    }
    if (got == 0) {
      break;
    }
    len += (size_t) got;
  }
  *out_data = buffer;
  *out_len = len;
  return 0;
}

static void emit_to_stdout(void *ctx, const unsigned char *data, size_t len) {
  (void) ctx;
  if (len > 0) {
    fwrite(data, 1, len, stdout);
  }
}

static int cmd_path_safe(int argc, char **argv) {
  if (argc != 3) {
    fprintf(stderr, "usage: %s path-safe <entry-name>\n", argv[0]);
    return 2;
  }
  printf("%d\n", ish_path_is_safe_entry_name(argv[2]));
  return 0;
}

static int cmd_path_join(int argc, char **argv) {
  if (argc != 4) {
    fprintf(stderr, "usage: %s path-join <root> <relative>\n", argv[0]);
    return 2;
  }
  char out[4096];
  if (!ish_path_join_within_root(argv[2], argv[3], out, sizeof(out))) {
    printf("UNSAFE\n");
    return 0;
  }
  printf("%s\n", out);
  return 0;
}

static int cmd_extract(int argc, char **argv) {
  if (argc != 4) {
    fprintf(stderr, "usage: %s extract <archive.tar.gz> <dest-dir>\n", argv[0]);
    return 2;
  }
  int status = ish_rootfs_extract(argv[2], argv[3]);
  printf("%d\n", status);
  return 0;
}

static int cmd_fakefsify(int argc, char **argv) {
  if (argc != 3) {
    fprintf(stderr, "usage: %s fakefsify <rootfs-dir>\n", argv[0]);
    return 2;
  }
  int status = ish_rootfs_prepare_fakefs(argv[2]);
  printf("%d\n", status);
  return 0;
}

static int cmd_documents_script(int argc, char **argv) {
  if (argc != 4) {
    fprintf(stderr, "usage: %s documents-script <rootfs-dir> <host-documents-path>\n",
            argv[0]);
    return 2;
  }
  int status = ish_rootfs_write_documents_mount_script(argv[2], argv[3]);
  printf("%d\n", status);
  return 0;
}

static int cmd_resolv_conf_prepare(int argc, char **argv) {
  if (argc != 3) {
    fprintf(stderr, "usage: %s resolv-conf-prepare <rootfs-dir>\n", argv[0]);
    return 2;
  }
  int status = ish_rootfs_prepare_resolv_conf(argv[2]);
  printf("%d\n", status);
  return 0;
}

static int cmd_resolv_conf_update(int argc, char **argv) {
  if (argc != 3) {
    fprintf(stderr, "usage: %s resolv-conf-update <rootfs-dir>\n", argv[0]);
    return 2;
  }
  unsigned char *contents = NULL;
  size_t length = 0;
  if (read_all_stdin(&contents, &length) != 0) {
    fprintf(stderr, "failed to read stdin\n");
    return 2;
  }
  int status = ish_rootfs_update_resolv_conf(argv[2], (const char *) contents, length);
  free(contents);
  printf("%d\n", status);
  return 0;
}

static int cmd_wrap(int argc, char **argv) {
  (void) argc;
  (void) argv;
  unsigned char *data = NULL;
  size_t len = 0;
  if (read_all_stdin(&data, &len) != 0) {
    fprintf(stderr, "failed to read stdin\n");
    return 2;
  }
  char *command = malloc(len + 1);
  memcpy(command, data, len);
  command[len] = '\0';
  free(data);

  size_t out_size = len + 256;
  char *out = malloc(out_size);
  int written = ish_exit_protocol_wrap_command(command, out, out_size);
  if (written < 0 || (size_t) written >= out_size) {
    fprintf(stderr, "wrap failed or truncated (written=%d)\n", written);
    free(command);
    free(out);
    return 2;
  }
  fwrite(out, 1, (size_t) written, stdout);
  free(command);
  free(out);
  return 0;
}

static int cmd_scan(int argc, char **argv) {
  if (argc != 3) {
    fprintf(stderr, "usage: %s scan <chunk-size>\n", argv[0]);
    return 2;
  }
  long chunk_size = strtol(argv[2], NULL, 10);
  unsigned char *data = NULL;
  size_t len = 0;
  if (read_all_stdin(&data, &len) != 0) {
    fprintf(stderr, "failed to read stdin\n");
    return 2;
  }
  if (chunk_size <= 0) {
    chunk_size = (long) (len > 0 ? len : 1);
  }

  ish_exit_scanner scanner;
  ish_exit_scanner_init(&scanner);
  size_t offset = 0;
  while (offset < len) {
    size_t take = (size_t) chunk_size;
    if (take > len - offset) {
      take = len - offset;
    }
    ish_exit_scanner_feed(&scanner, data + offset, take, emit_to_stdout, NULL);
    offset += take;
  }
  fflush(stdout);
  free(data);
  if (scanner.matched) {
    fprintf(stderr, "MATCHED %d\n", scanner.exit_code);
  } else {
    fprintf(stderr, "NOMATCH\n");
  }
  return 0;
}

int main(int argc, char **argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <path-safe|path-join|extract|fakefsify|documents-script|resolv-conf-prepare|resolv-conf-update|wrap|scan> ...\n", argv[0]);
    return 2;
  }
  if (strcmp(argv[1], "path-safe") == 0) {
    return cmd_path_safe(argc, argv);
  }
  if (strcmp(argv[1], "path-join") == 0) {
    return cmd_path_join(argc, argv);
  }
  if (strcmp(argv[1], "extract") == 0) {
    return cmd_extract(argc, argv);
  }
  if (strcmp(argv[1], "fakefsify") == 0) {
    return cmd_fakefsify(argc, argv);
  }
  if (strcmp(argv[1], "documents-script") == 0) {
    return cmd_documents_script(argc, argv);
  }
  if (strcmp(argv[1], "resolv-conf-prepare") == 0) {
    return cmd_resolv_conf_prepare(argc, argv);
  }
  if (strcmp(argv[1], "resolv-conf-update") == 0) {
    return cmd_resolv_conf_update(argc, argv);
  }
  if (strcmp(argv[1], "wrap") == 0) {
    return cmd_wrap(argc, argv);
  }
  if (strcmp(argv[1], "scan") == 0) {
    return cmd_scan(argc, argv);
  }
  fprintf(stderr, "unknown subcommand: %s\n", argv[1]);
  return 2;
}
