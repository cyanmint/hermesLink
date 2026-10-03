/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#ifndef _DEFAULT_SOURCE
#define _DEFAULT_SOURCE
#endif
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include "ish_rootfs.h"
#include "ish_path_safety.h"

#include <zlib.h>

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define ISH_TAR_BLOCK_SIZE 512
#define ISH_TAR_NAME_LEN 100
#define ISH_TAR_PREFIX_LEN 155
#define ISH_TAR_PATH_MAX (ISH_TAR_NAME_LEN + 1 + ISH_TAR_PREFIX_LEN + 1)

struct ish_tar_header {
  char name[ISH_TAR_NAME_LEN];
  char mode[8];
  char uid[8];
  char gid[8];
  char size[12];
  char mtime[12];
  char chksum[8];
  char typeflag;
  char linkname[ISH_TAR_NAME_LEN];
  char magic[6];
  char version[2];
  char uname[32];
  char gname[32];
  char devmajor[8];
  char devminor[8];
  char prefix[ISH_TAR_PREFIX_LEN];
  char padding[12];
};

typedef struct {
  char *path;
  mode_t mode;
} ish_directory_mode;

static int ish_block_is_all_zero(const unsigned char *block) {
  for (int i = 0; i < ISH_TAR_BLOCK_SIZE; i++) {
    if (block[i] != 0) {
      return 0;
    }
  }
  return 1;
}

static long ish_parse_octal_field(const char *field, unsigned long field_len) {
  long value = 0;
  for (unsigned long i = 0; i < field_len; i++) {
    unsigned char c = (unsigned char) field[i];
    if (c == '\0' || c == ' ') {
      continue;
    }
    if (c < '0' || c > '7') {
      return -1;
    }
    value = value * 8 + (c - '0');
  }
  return value;
}

static void ish_copy_field(char *out, unsigned long out_size, const char *field, unsigned long field_len) {
  unsigned long len = field_len;
  if (len >= out_size) {
    len = out_size - 1;
  }
  /* ustar text fields are NUL-padded but not guaranteed NUL-terminated if
   * they fill the whole field; always terminate defensively. */
  unsigned long actual = 0;
  while (actual < len && field[actual] != '\0') {
    actual++;
  }
  memcpy(out, field, actual);
  out[actual] = '\0';
}

static int ish_mkdir_component_safe(const char *path) {
  struct stat st;
  if (lstat(path, &st) == 0) {
    if (!S_ISDIR(st.st_mode)) {
      /* Refuse to follow or replace an existing non-directory (in
       * particular a symlink) at an intermediate path component. */
      errno = EEXIST;
      return -1;
    }
    return 0;
  }
  if (errno != ENOENT) {
    return -1;
  }
  if (mkdir(path, 0755) != 0 && errno != EEXIST) {
    return -1;
  }
  return 0;
}

/* Creates every directory component of `path` (which must already have
 * been validated with ish_path_is_safe_entry_name/ish_path_join_within_root),
 * refusing to traverse through any existing non-directory component.
 * `create_last` controls whether the final path component itself is
 * created as a directory (for directory entries) or left for the caller
 * to create as a file/symlink (regular files, symlinks). */
static int ish_mkdir_parents(char *path, int create_last) {
  char *cursor = path;
  if (*cursor == '/') {
    cursor++;
  }
  for (;;) {
    char *slash = strchr(cursor, '/');
    if (slash == NULL) {
      break;
    }
    *slash = '\0';
    int rc = ish_mkdir_component_safe(path);
    *slash = '/';
    if (rc != 0) {
      return -1;
    }
    cursor = slash + 1;
  }
  if (create_last) {
    return ish_mkdir_component_safe(path);
  }
  return 0;
}

static int ish_record_directory_mode(ish_directory_mode **modes, size_t *count,
                                     size_t *capacity, const char *path, mode_t mode) {
  for (size_t i = 0; i < *count; i++) {
    if (strcmp((*modes)[i].path, path) == 0) {
      (*modes)[i].mode = mode;
      return 0;
    }
  }
  if (*count == *capacity) {
    size_t new_capacity = *capacity == 0 ? 16 : *capacity * 2;
    ish_directory_mode *new_modes = realloc(*modes, new_capacity * sizeof(**modes));
    if (new_modes == NULL) {
      return -1;
    }
    *modes = new_modes;
    *capacity = new_capacity;
  }
  char *copy = strdup(path);
  if (copy == NULL) {
    return -1;
  }
  (*modes)[*count].path = copy;
  (*modes)[*count].mode = mode;
  (*count)++;
  return 0;
}

static int ish_apply_directory_modes(ish_directory_mode *modes, size_t count) {
  /* Restore child directories first so restrictive parent modes cannot block
   * finalizing their descendants. */
  while (count > 0) {
    count--;
    if (chmod(modes[count].path, modes[count].mode) != 0) {
      return -1;
    }
  }
  return 0;
}

static void ish_free_directory_modes(ish_directory_mode *modes, size_t count) {
  for (size_t i = 0; i < count; i++) {
    free(modes[i].path);
  }
  free(modes);
}

/* Every tar entry body is padded to a 512-byte boundary. `consumed` is how
 * many of the `size` logical bytes the caller already read (0 for entries
 * whose body is skipped entirely, such as symlinks, or the body size for
 * entries already streamed to a destination file); this discards exactly
 * the remaining unread bytes through the next block boundary. */
static int ish_discard_entry_remainder(gzFile archive, long size, long consumed) {
  long padded = ((size + ISH_TAR_BLOCK_SIZE - 1) / ISH_TAR_BLOCK_SIZE) * ISH_TAR_BLOCK_SIZE;
  long remaining = padded - consumed;
  unsigned char scratch[4096];
  while (remaining > 0) {
    int chunk = remaining < (long) sizeof(scratch) ? (int) remaining : (int) sizeof(scratch);
    int got = gzread(archive, scratch, (unsigned) chunk);
    if (got != chunk) {
      return -1;
    }
    remaining -= chunk;
  }
  return 0;
}

static int ish_extract_regular_file(gzFile archive, const char *dest_path, long size, unsigned long mode) {
  int fd = open(dest_path, O_WRONLY | O_CREAT | O_TRUNC | O_NOFOLLOW, (mode_t) (mode ? (mode & 0777) : 0644));
  if (fd < 0) {
    return -1;
  }
  long remaining = size;
  unsigned char buffer[8192];
  int ok = 1;
  while (remaining > 0) {
    int chunk = remaining < (long) sizeof(buffer) ? (int) remaining : (int) sizeof(buffer);
    int got = gzread(archive, buffer, (unsigned) chunk);
    if (got != chunk) {
      ok = 0;
      break;
    }
    size_t offset = 0;
    while (offset < (size_t) chunk) {
      ssize_t written = write(fd, buffer + offset, (size_t) chunk - offset);
      if (written < 0 && errno == EINTR) {
        continue;
      }
      if (written <= 0) {
        if (written == 0) {
          errno = EIO;
        }
        ok = 0;
        break;
      }
      offset += (size_t) written;
    }
    if (!ok) {
      break;
    }
    remaining -= chunk;
  }
  close(fd);
  if (!ok) {
    return -1;
  }
  return 0;
}

int ish_rootfs_extract(const char *archive_path, const char *dest_root) {
  if (archive_path == NULL || dest_root == NULL) {
    return ISH_ROOTFS_ERR_DEST;
  }
  struct stat root_stat;
  if (stat(dest_root, &root_stat) != 0 || !S_ISDIR(root_stat.st_mode)) {
    return ISH_ROOTFS_ERR_DEST;
  }

  gzFile archive = gzopen(archive_path, "rb");
  if (archive == NULL) {
    return ISH_ROOTFS_ERR_OPEN;
  }

  int result = ISH_ROOTFS_OK;
  int io_errno = 0;
  unsigned char block[ISH_TAR_BLOCK_SIZE];
  int consecutive_zero_blocks = 0;
  ish_directory_mode *directory_modes = NULL;
  size_t directory_mode_count = 0;
  size_t directory_mode_capacity = 0;

  for (;;) {
    int got = gzread(archive, block, ISH_TAR_BLOCK_SIZE);
    if (got == 0) {
      break; /* clean end of stream */
    }
    if (got != ISH_TAR_BLOCK_SIZE) {
      result = ISH_ROOTFS_ERR_READ;
      break;
    }
    if (ish_block_is_all_zero(block)) {
      consecutive_zero_blocks++;
      if (consecutive_zero_blocks >= 2) {
        break; /* standard tar end-of-archive marker */
      }
      continue;
    }
    consecutive_zero_blocks = 0;

    struct ish_tar_header header;
    memcpy(&header, block, sizeof(header));
    if (memcmp(header.magic, "ustar", 5) != 0) {
      result = ISH_ROOTFS_ERR_FORMAT;
      break;
    }

    char name[ISH_TAR_PATH_MAX];
    char prefix[ISH_TAR_PREFIX_LEN + 1];
    ish_copy_field(prefix, sizeof(prefix), header.prefix, ISH_TAR_PREFIX_LEN);
    if (prefix[0] != '\0') {
      char tail[ISH_TAR_NAME_LEN + 1];
      ish_copy_field(tail, sizeof(tail), header.name, ISH_TAR_NAME_LEN);
      snprintf(name, sizeof(name), "%s/%s", prefix, tail);
    } else {
      ish_copy_field(name, sizeof(name), header.name, ISH_TAR_NAME_LEN);
    }

    long size = ish_parse_octal_field(header.size, sizeof(header.size));
    long mode = ish_parse_octal_field(header.mode, sizeof(header.mode));
    if (size < 0 || mode < 0) {
      result = ISH_ROOTFS_ERR_FORMAT;
      break;
    }

    /* A trailing '/' on a directory entry name is conventional; strip it
     * so ish_path_is_safe_entry_name sees a normal relative path. */
    unsigned long name_len = (unsigned long) strlen(name);
    if (name_len > 1 && name[name_len - 1] == '/') {
      name[name_len - 1] = '\0';
    }

    if (!ish_path_is_safe_entry_name(name)) {
      result = ISH_ROOTFS_ERR_UNSAFE_PATH;
      break;
    }

    char dest_path[4096];
    if (!ish_path_join_within_root(dest_root, name, dest_path, sizeof(dest_path))) {
      result = ISH_ROOTFS_ERR_UNSAFE_PATH;
      break;
    }

    char typeflag = header.typeflag;
    if (typeflag == '5') {
      if (ish_mkdir_parents(dest_path, 1) != 0) {
        result = ISH_ROOTFS_ERR_IO;
        io_errno = errno != 0 ? errno : EIO;
        break;
      }
      if (ish_record_directory_mode(&directory_modes, &directory_mode_count,
                                    &directory_mode_capacity, dest_path,
                                    (mode_t) (mode & 0777)) != 0) {
        result = ISH_ROOTFS_ERR_IO;
        io_errno = errno != 0 ? errno : ENOMEM;
        break;
      }
      if (ish_discard_entry_remainder(archive, size, 0) != 0) {
        result = ISH_ROOTFS_ERR_READ;
        break;
      }
    } else if (typeflag == '0' || typeflag == '\0') {
      if (ish_mkdir_parents(dest_path, 0) != 0) {
        result = ISH_ROOTFS_ERR_IO;
        io_errno = errno != 0 ? errno : EIO;
        break;
      }
      if (ish_extract_regular_file(archive, dest_path, size, (unsigned long) mode) != 0) {
        result = ISH_ROOTFS_ERR_IO;
        io_errno = errno != 0 ? errno : EIO;
        break;
      }
      if (ish_discard_entry_remainder(archive, size, size) != 0) {
        result = ISH_ROOTFS_ERR_READ;
        break;
      }
    } else if (typeflag == '2') {
      char linkname[ISH_TAR_NAME_LEN + 1];
      ish_copy_field(linkname, sizeof(linkname), header.linkname, ISH_TAR_NAME_LEN);
      if (!ish_path_is_safe_link_target(linkname)) {
        result = ISH_ROOTFS_ERR_UNSAFE_PATH;
        break;
      }
      if (ish_mkdir_parents(dest_path, 0) != 0) {
        result = ISH_ROOTFS_ERR_IO;
        io_errno = errno != 0 ? errno : EIO;
        break;
      }
      unlink(dest_path); /* fresh extraction: replace a prior symlink/file if present */
      if (symlink(linkname, dest_path) != 0) {
        result = ISH_ROOTFS_ERR_IO;
        io_errno = errno != 0 ? errno : EIO;
        break;
      }
      if (ish_discard_entry_remainder(archive, size, 0) != 0) {
        result = ISH_ROOTFS_ERR_READ;
        break;
      }
    } else {
      result = ISH_ROOTFS_ERR_UNSUPPORTED_TYPE;
      break;
    }
  }

  if (result == ISH_ROOTFS_OK &&
      ish_apply_directory_modes(directory_modes, directory_mode_count) != 0) {
    result = ISH_ROOTFS_ERR_IO;
    io_errno = errno != 0 ? errno : EIO;
  }
  ish_free_directory_modes(directory_modes, directory_mode_count);
  gzclose(archive);
  if (result == ISH_ROOTFS_ERR_IO) {
    errno = io_errno != 0 ? io_errno : EIO;
  }
  return result;
}
