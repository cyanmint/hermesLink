/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#include "ish_path_safety.h"

#include <string.h>

static int ish_path_has_dotdot_component(const char *path) {
  const char *cursor = path;
  while (*cursor != '\0') {
    const char *segment_start = cursor;
    while (*cursor != '\0' && *cursor != '/') {
      cursor++;
    }
    unsigned long len = (unsigned long) (cursor - segment_start);
    if (len == 2 && segment_start[0] == '.' && segment_start[1] == '.') {
      return 1;
    }
    if (*cursor == '/') {
      cursor++;
    }
  }
  return 0;
}

int ish_path_is_safe_entry_name(const char *entry_name) {
  if (entry_name == NULL || entry_name[0] == '\0') {
    return 0;
  }
  if (entry_name[0] == '/') {
    return 0;
  }
  if (ish_path_has_dotdot_component(entry_name)) {
    return 0;
  }
  return 1;
}

int ish_path_is_safe_link_target(const char *link_target) {
  if (link_target == NULL || link_target[0] == '\0') {
    return 0;
  }
  return 1;
}

int ish_path_join_within_root(const char *root, const char *relative, char *out, unsigned long out_size) {
  if (root == NULL || relative == NULL || out == NULL || out_size == 0) {
    return 0;
  }
  if (!ish_path_is_safe_entry_name(relative)) {
    return 0;
  }
  unsigned long root_len = (unsigned long) strlen(root);
  unsigned long relative_len = (unsigned long) strlen(relative);
  /* root + '/' + relative + '\0' */
  if (root_len + 1 + relative_len + 1 > out_size) {
    return 0;
  }
  memcpy(out, root, root_len);
  out[root_len] = '/';
  memcpy(out + root_len + 1, relative, relative_len);
  out[root_len + 1 + relative_len] = '\0';
  return 1;
}
