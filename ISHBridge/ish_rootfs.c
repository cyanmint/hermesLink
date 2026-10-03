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

#include <sqlite3.h>
#include <zlib.h>

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdint.h>
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

typedef struct {
  uint32_t mode;
  uint32_t uid;
  uint32_t gid;
  uint32_t rdev;
} ish_fakefs_stat;

static int ish_fakefs_exec(sqlite3 *db, const char *sql) {
  char *error = NULL;
  int status = sqlite3_exec(db, sql, NULL, NULL, &error);
  sqlite3_free(error);
  return status == SQLITE_OK ? 0 : -1;
}

static int ish_fakefs_store_path(sqlite3 *db, sqlite3_stmt *insert_stat,
                                 sqlite3_stmt *insert_path, const char *path,
                                 mode_t mode) {
  ish_fakefs_stat stat = {
      .mode = (uint32_t) mode,
      .uid = 0,
      .gid = 0,
      .rdev = 0,
  };
  int status = sqlite3_bind_blob(insert_stat, 1, &stat, sizeof(stat), SQLITE_TRANSIENT);
  if (status == SQLITE_OK) {
    status = sqlite3_step(insert_stat);
  }
  if (status != SQLITE_DONE) {
    sqlite3_reset(insert_stat);
    sqlite3_clear_bindings(insert_stat);
    return -1;
  }
  sqlite3_reset(insert_stat);
  sqlite3_clear_bindings(insert_stat);

  status = sqlite3_bind_blob(insert_path, 1, path, (int) strlen(path), SQLITE_TRANSIENT);
  if (status == SQLITE_OK) {
    status = sqlite3_bind_int64(insert_path, 2, sqlite3_last_insert_rowid(db));
  }
  if (status == SQLITE_OK) {
    status = sqlite3_step(insert_path);
  }
  sqlite3_reset(insert_path);
  sqlite3_clear_bindings(insert_path);
  return status == SQLITE_DONE ? 0 : -1;
}

static int ish_fakefs_raw_root_is_valid(const char *root) {
  const char *paths[] = {"bin/busybox", "etc/alpine-release", "sbin/init"};
  for (size_t i = 0; i < sizeof(paths) / sizeof(paths[0]); i++) {
    char path[4096];
    if (snprintf(path, sizeof(path), "%s/%s", root, paths[i]) >= (int) sizeof(path)) {
      return 0;
    }
    struct stat stat;
    if (lstat(path, &stat) != 0) {
      return 0;
    }
    if ((i == 0 && (!S_ISREG(stat.st_mode) || (stat.st_mode & 0111) == 0)) ||
        (i == 1 && !S_ISREG(stat.st_mode)) ||
        (i == 2 && !S_ISLNK(stat.st_mode) && !S_ISREG(stat.st_mode))) {
      return 0;
    }
  }
  return 1;
}

static int ish_fakefs_move_path(const char *source, const char *destination) {
  struct stat source_stat;
  if (lstat(source, &source_stat) != 0) {
    return -1;
  }
  struct stat destination_stat;
  if (lstat(destination, &destination_stat) == 0) {
    errno = EEXIST;
    return -1;
  }
  if (errno != ENOENT) {
    return -1;
  }

  mode_t original_mode = source_stat.st_mode & 07777;
  int is_directory = S_ISDIR(source_stat.st_mode);
  if (is_directory && chmod(source, original_mode | S_IWUSR) != 0) {
    return -1;
  }
  if (rename(source, destination) != 0) {
    int saved_errno = errno;
    if (is_directory) {
      chmod(source, original_mode);
    }
    errno = saved_errno;
    return -1;
  }
  if (is_directory && chmod(destination, original_mode) != 0) {
    return -1;
  }
  return 0;
}

static int ish_fakefs_make_temporary_path(const char *root, const char *label,
                                          char *path, size_t path_size) {
  for (unsigned int attempt = 0; attempt < 100; attempt++) {
    int written = snprintf(path, path_size, "%s/.hermeslink-%s-%ld-%u",
                           root, label, (long) getpid(), attempt);
    if (written < 0 || (size_t) written >= path_size) {
      errno = ENAMETOOLONG;
      return -1;
    }
    struct stat stat;
    if (lstat(path, &stat) != 0) {
      return errno == ENOENT ? 0 : -1;
    }
  }
  errno = EEXIST;
  return -1;
}

static int ish_fakefs_index_tree(sqlite3 *db, sqlite3_stmt *insert_stat,
                                 sqlite3_stmt *insert_path, const char *data_root,
                                 const char *relative_path, mode_t root_mode) {
  char directory_path[4096];
  if (relative_path[0] == '\0') {
    if (snprintf(directory_path, sizeof(directory_path), "%s", data_root) >=
        (int) sizeof(directory_path)) {
      errno = ENAMETOOLONG;
      return -1;
    }
  } else if (snprintf(directory_path, sizeof(directory_path), "%s/%s",
                      data_root, relative_path) >= (int) sizeof(directory_path)) {
    errno = ENAMETOOLONG;
    return -1;
  }

  struct stat directory_stat;
  if (lstat(directory_path, &directory_stat) != 0 || !S_ISDIR(directory_stat.st_mode)) {
    return -1;
  }
  mode_t stored_mode = relative_path[0] == '\0' ? root_mode : directory_stat.st_mode;
  if (ish_fakefs_store_path(db, insert_stat, insert_path, relative_path,
                            stored_mode) != 0 ||
      chmod(directory_path, 0777) != 0) {
    return -1;
  }

  DIR *directory = opendir(directory_path);
  if (directory == NULL) {
    return -1;
  }
  int result = 0;
  struct dirent *entry;
  while ((entry = readdir(directory)) != NULL) {
    if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
      continue;
    }
    char child_path[4096];
    int written = relative_path[0] == '\0'
        ? snprintf(child_path, sizeof(child_path), "%s", entry->d_name)
        : snprintf(child_path, sizeof(child_path), "%s/%s", relative_path, entry->d_name);
    if (written < 0 || written >= (int) sizeof(child_path)) {
      errno = ENAMETOOLONG;
      result = -1;
      break;
    }
    char host_path[4096];
    written = snprintf(host_path, sizeof(host_path), "%s/%s", data_root, child_path);
    if (written < 0 || written >= (int) sizeof(host_path)) {
      errno = ENAMETOOLONG;
      result = -1;
      break;
    }

    struct stat child_stat;
    if (lstat(host_path, &child_stat) != 0) {
      result = -1;
      break;
    }
    if (S_ISDIR(child_stat.st_mode)) {
      if (ish_fakefs_index_tree(db, insert_stat, insert_path, data_root, child_path,
                                root_mode) != 0) {
        result = -1;
        break;
      }
    } else if (S_ISREG(child_stat.st_mode)) {
      if (ish_fakefs_store_path(db, insert_stat, insert_path, child_path,
                                child_stat.st_mode) != 0 ||
          chmod(host_path, 0666) != 0) {
        result = -1;
        break;
      }
    } else if (S_ISLNK(child_stat.st_mode)) {
      char link_target[PATH_MAX + 1];
      ssize_t target_length = readlink(host_path, link_target, PATH_MAX);
      if (target_length <= 0 || target_length >= PATH_MAX) {
        errno = EINVAL;
        result = -1;
        break;
      }
      link_target[target_length] = '\0';
      if (unlink(host_path) != 0) {
        result = -1;
        break;
      }
      int fd = open(host_path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0666);
      if (fd < 0) {
        result = -1;
        break;
      }
      size_t offset = 0;
      while (offset < (size_t) target_length) {
        ssize_t count = write(fd, link_target + offset, (size_t) target_length - offset);
        if (count < 0 && errno == EINTR) {
          continue;
        }
        if (count <= 0) {
          if (count == 0) {
            errno = EIO;
          }
          result = -1;
          break;
        }
        offset += (size_t) count;
      }
      close(fd);
      if (result != 0 ||
          ish_fakefs_store_path(db, insert_stat, insert_path, child_path,
                                child_stat.st_mode) != 0) {
        result = -1;
        break;
      }
    } else {
      errno = ENOTSUP;
      result = -1;
      break;
    }
  }
  closedir(directory);
  return result;
}

static int ish_fakefs_create_database(const char *root, const char *data_root,
                                      mode_t root_mode) {
  char database_path[4096];
  if (snprintf(database_path, sizeof(database_path), "%s/meta.db", root) >=
      (int) sizeof(database_path)) {
    errno = ENAMETOOLONG;
    return -1;
  }

  sqlite3 *db = NULL;
  if (sqlite3_open_v2(database_path, &db,
                      SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE, NULL) != SQLITE_OK) {
    sqlite3_close(db);
    return -1;
  }
  int result = -1;
  sqlite3_stmt *insert_stat = NULL;
  sqlite3_stmt *insert_path = NULL;
  if (ish_fakefs_exec(db,
      "PRAGMA journal_mode=DELETE;"
      "BEGIN;"
      "CREATE TABLE meta (id INTEGER UNIQUE DEFAULT 0, db_inode INTEGER);"
      "INSERT INTO meta (db_inode) VALUES (0);"
      "CREATE TABLE stats (inode INTEGER PRIMARY KEY, stat BLOB);"
      "CREATE TABLE paths (path BLOB PRIMARY KEY, inode INTEGER REFERENCES stats(inode));"
      "CREATE INDEX inode_to_path ON paths (inode, path);"
      "PRAGMA user_version=3;") != 0 ||
      sqlite3_prepare_v2(db, "INSERT INTO stats (stat) VALUES (?)", -1,
                         &insert_stat, NULL) != SQLITE_OK ||
      sqlite3_prepare_v2(db, "INSERT OR REPLACE INTO paths (path, inode) VALUES (?, ?)", -1,
                         &insert_path, NULL) != SQLITE_OK) {
    goto cleanup;
  }
  if (ish_fakefs_index_tree(db, insert_stat, insert_path, data_root, "", root_mode) != 0 ||
      ish_fakefs_exec(db, "COMMIT;") != 0) {
    ish_fakefs_exec(db, "ROLLBACK;");
    goto cleanup;
  }
  result = 0;

cleanup:
  sqlite3_finalize(insert_stat);
  sqlite3_finalize(insert_path);
  sqlite3_close(db);
  return result;
}

static int ish_fakefs_database_is_valid(const char *database_path) {
  sqlite3 *db = NULL;
  if (sqlite3_open_v2(database_path, &db, SQLITE_OPEN_READONLY, NULL) != SQLITE_OK) {
    sqlite3_close(db);
    return 0;
  }
  sqlite3_stmt *statement = NULL;
  int valid = sqlite3_prepare_v2(db,
      "SELECT db_inode FROM meta LIMIT 1", -1, &statement, NULL) == SQLITE_OK &&
      sqlite3_step(statement) == SQLITE_ROW;
  sqlite3_finalize(statement);
  statement = NULL;
  valid = valid &&
      sqlite3_prepare_v2(db,
          "SELECT stats.stat FROM paths JOIN stats ON stats.inode = paths.inode WHERE paths.path = ?",
          -1, &statement, NULL) == SQLITE_OK;
  const char *required_paths[] = {
      "", "bin/busybox", "etc/alpine-release", "sbin/init",
  };
  for (size_t i = 0; valid && i < sizeof(required_paths) / sizeof(required_paths[0]); i++) {
    ish_fakefs_stat stat;
    int path_length = (int) strlen(required_paths[i]);
    if (sqlite3_bind_blob(statement, 1, required_paths[i], path_length, SQLITE_STATIC) != SQLITE_OK ||
        sqlite3_step(statement) != SQLITE_ROW ||
        sqlite3_column_bytes(statement, 0) != (int) sizeof(stat)) {
      valid = 0;
    } else {
      memcpy(&stat, sqlite3_column_blob(statement, 0), sizeof(stat));
      mode_t type = stat.mode & S_IFMT;
      if ((i == 0 && type != S_IFDIR) ||
          (i == 1 && (type != S_IFREG || (stat.mode & 0111) == 0)) ||
          (i == 2 && type != S_IFREG) ||
          (i == 3 && type != S_IFLNK && type != S_IFREG)) {
        valid = 0;
      }
    }
    sqlite3_reset(statement);
    sqlite3_clear_bindings(statement);
  }
  sqlite3_finalize(statement);
  sqlite3_close(db);
  return valid;
}

static int ish_fakefs_move_entries(const char *root, const char *data_root,
                                   const char *temporary_data_name,
                                   const char *temporary_database_name) {
  DIR *directory = opendir(root);
  if (directory == NULL) {
    return -1;
  }
  int result = 0;
  struct dirent *entry;
  while ((entry = readdir(directory)) != NULL) {
    if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0 ||
        strcmp(entry->d_name, "data") == 0 || strcmp(entry->d_name, "meta.db") == 0 ||
        (temporary_data_name != NULL && strcmp(entry->d_name, temporary_data_name) == 0) ||
        (temporary_database_name != NULL &&
         strcmp(entry->d_name, temporary_database_name) == 0)) {
      continue;
    }
    char source[4096];
    char destination[4096];
    if (snprintf(source, sizeof(source), "%s/%s", root, entry->d_name) >=
            (int) sizeof(source) ||
        snprintf(destination, sizeof(destination), "%s/%s", data_root, entry->d_name) >=
            (int) sizeof(destination)) {
      errno = ENAMETOOLONG;
      result = -1;
      break;
    }
    if (ish_fakefs_move_path(source, destination) != 0) {
      result = -1;
      break;
    }
  }
  closedir(directory);
  return result;
}

int ish_rootfs_prepare_fakefs(const char *root) {
  if (root == NULL || root[0] == '\0') {
    errno = EINVAL;
    return ISH_ROOTFS_ERR_DEST;
  }
  char data_root[4096];
  char database_path[4096];
  if (snprintf(data_root, sizeof(data_root), "%s/data", root) >= (int) sizeof(data_root) ||
      snprintf(database_path, sizeof(database_path), "%s/meta.db", root) >=
          (int) sizeof(database_path)) {
    errno = ENAMETOOLONG;
    return ISH_ROOTFS_ERR_DEST;
  }
  struct stat data_stat;
  struct stat database_stat;
  int have_data_entry = lstat(data_root, &data_stat) == 0;
  int have_database_entry = lstat(database_path, &database_stat) == 0;
  int have_data = have_data_entry && S_ISDIR(data_stat.st_mode);
  int have_database = have_database_entry && S_ISREG(database_stat.st_mode) &&
      database_stat.st_size > 0;
  if (have_data && have_database) {
    if (ish_fakefs_database_is_valid(database_path)) {
      return ISH_ROOTFS_OK;
    }
    if (!ish_fakefs_raw_root_is_valid(root)) {
      return ISH_ROOTFS_ERR_FORMAT;
    }
  }
  if (!ish_fakefs_raw_root_is_valid(root)) {
    return ISH_ROOTFS_ERR_FORMAT;
  }
  struct stat root_stat;
  if (lstat(root, &root_stat) != 0 || !S_ISDIR(root_stat.st_mode)) {
    errno = ENOTDIR;
    return ISH_ROOTFS_ERR_DEST;
  }
  mode_t root_mode = root_stat.st_mode;
  if (chmod(root, 0777) != 0) {
    return ISH_ROOTFS_ERR_IO;
  }
  char temporary_data[4096];
  char temporary_database[4096];
  int has_temporary_data = 0;
  int has_temporary_database = 0;
  if (have_data_entry) {
    if (ish_fakefs_make_temporary_path(root, "raw-data", temporary_data,
                                       sizeof(temporary_data)) != 0 ||
        ish_fakefs_move_path(data_root, temporary_data) != 0) {
      return ISH_ROOTFS_ERR_IO;
    }
    has_temporary_data = 1;
  }
  if (have_database_entry) {
    if (ish_fakefs_make_temporary_path(root, "raw-meta", temporary_database,
                                       sizeof(temporary_database)) != 0 ||
        ish_fakefs_move_path(database_path, temporary_database) != 0) {
      return ISH_ROOTFS_ERR_IO;
    }
    has_temporary_database = 1;
  }
  if (mkdir(data_root, 0777) != 0) {
    return ISH_ROOTFS_ERR_IO;
  }
  const char *temporary_data_name = has_temporary_data
      ? strrchr(temporary_data, '/') + 1 : NULL;
  const char *temporary_database_name = has_temporary_database
      ? strrchr(temporary_database, '/') + 1 : NULL;
  if (ish_fakefs_move_entries(root, data_root, temporary_data_name,
                              temporary_database_name) != 0) {
    return ISH_ROOTFS_ERR_IO;
  }
  if (has_temporary_data) {
    char guest_data_path[4096];
    if (snprintf(guest_data_path, sizeof(guest_data_path), "%s/data", data_root) >=
        (int) sizeof(guest_data_path) ||
        ish_fakefs_move_path(temporary_data, guest_data_path) != 0) {
      return ISH_ROOTFS_ERR_IO;
    }
  }
  if (has_temporary_database) {
    char guest_meta_path[4096];
    if (snprintf(guest_meta_path, sizeof(guest_meta_path), "%s/meta.db", data_root) >=
        (int) sizeof(guest_meta_path) ||
        ish_fakefs_move_path(temporary_database, guest_meta_path) != 0) {
      return ISH_ROOTFS_ERR_IO;
    }
  }
  char sidecar_path[4096];
  if (snprintf(sidecar_path, sizeof(sidecar_path), "%s-wal", database_path) >=
      (int) sizeof(sidecar_path)) {
    errno = ENAMETOOLONG;
    return ISH_ROOTFS_ERR_DEST;
  }
  unlink(sidecar_path);
  if (snprintf(sidecar_path, sizeof(sidecar_path), "%s-shm", database_path) >=
      (int) sizeof(sidecar_path)) {
    errno = ENAMETOOLONG;
    return ISH_ROOTFS_ERR_DEST;
  }
  unlink(sidecar_path);
  if (ish_fakefs_create_database(root, data_root, root_mode) != 0) {
    return ISH_ROOTFS_ERR_IO;
  }
  if (!ish_fakefs_database_is_valid(database_path)) {
    errno = EINVAL;
    return ISH_ROOTFS_ERR_FORMAT;
  }
  return ISH_ROOTFS_OK;
}

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

static int ish_normalize_entry_name(const char *name, char *normalized,
                                    size_t normalized_size) {
  size_t output_length = 0;
  const char *cursor = name;
  while (*cursor != '\0') {
    while (*cursor == '/') {
      cursor++;
    }
    if (*cursor == '\0') {
      break;
    }
    const char *component = cursor;
    while (*cursor != '\0' && *cursor != '/') {
      cursor++;
    }
    size_t component_length = (size_t) (cursor - component);
    if (component_length == 1 && component[0] == '.') {
      continue;
    }
    if (output_length != 0) {
      if (output_length + 1 >= normalized_size) {
        return 0;
      }
      normalized[output_length++] = '/';
    }
    if (component_length >= normalized_size - output_length) {
      return 0;
    }
    memcpy(normalized + output_length, component, component_length);
    output_length += component_length;
  }
  normalized[output_length] = '\0';
  return 1;
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
    char normalized_name[ISH_TAR_PATH_MAX];
    if (!ish_normalize_entry_name(name, normalized_name, sizeof(normalized_name))) {
      result = ISH_ROOTFS_ERR_UNSAFE_PATH;
      break;
    }
    if (normalized_name[0] == '\0') {
      if (header.typeflag != '5' || ish_discard_entry_remainder(archive, size, 0) != 0) {
        result = header.typeflag == '5' ? ISH_ROOTFS_ERR_READ : ISH_ROOTFS_ERR_UNSAFE_PATH;
        break;
      }
      continue;
    }

    char dest_path[4096];
    if (!ish_path_join_within_root(dest_root, normalized_name, dest_path, sizeof(dest_path))) {
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
