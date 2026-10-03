/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#import <Foundation/Foundation.h>

/* Pulled from the pinned, unmodified upstream iSH source checkout (see
 * hermes/build/fetch-ish-source.sh / hermes/build/build-ish-static.sh); the
 * header is vendored alongside the prebuilt static libraries this target
 * links against (install_ish_runtime.sh), never copied into this file. */
#include "LinuxInterop.h"

#include "ish_kernel_bridge.h"
#include "ish_rootfs.h"
#include "ish_exit_protocol.h"
#include "kernel/errno.h"
#include "kernel/fs.h"
#include "kernel/task.h"
#include "fs/fd.h"
#include "fs/path.h"
#include "fs/real.h"

#include <dispatch/dispatch.h>
#include <errno.h>
#include <netdb.h>
#include <netinet/in.h>
#include <pthread.h>
#include <resolv.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <SystemConfiguration/SystemConfiguration.h>
#include <time.h>
#include <unistd.h>

static pthread_mutex_t g_configuration_lock = PTHREAD_MUTEX_INITIALIZER;
static char g_configured_root[1024];
static ish_log_handler g_log_handler;
static int g_boot_started;
static pthread_mutex_t g_kernel_ready_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t g_kernel_ready_cond = PTHREAD_COND_INITIALIZER;
static int g_kernel_ready;
static int g_kernel_panicked;

static void ISHLog(const char *message) {
  pthread_mutex_lock(&g_configuration_lock);
  ish_log_handler handler = g_log_handler;
  pthread_mutex_unlock(&g_configuration_lock);
  if (handler != NULL) {
    handler(message);
  } else {
    NSLog(@"%s", message != NULL ? message : "ish: (empty diagnostic)");
  }
}

int ish_configure(const char *root_path, ish_log_handler log_handler) {
  if (root_path == NULL || root_path[0] == '\0' || strlen(root_path) >= sizeof(g_configured_root)) {
    return ISH_RUN_ERR_INVALID_ARGUMENT;
  }
  pthread_mutex_lock(&g_configuration_lock);
  if (g_boot_started &&
      (strcmp(g_configured_root, root_path) != 0 || g_log_handler != log_handler)) {
    pthread_mutex_unlock(&g_configuration_lock);
    return ISH_RUN_ERR_INVALID_ARGUMENT;
  }
  strlcpy(g_configured_root, root_path, sizeof(g_configured_root));
  g_log_handler = log_handler;
  pthread_mutex_unlock(&g_configuration_lock);
  return ISH_RUN_OK;
}

#pragma mark - sync_do_in_workqueue

/* LinuxInterop.h declares `sync_do_in_workqueue` as something iOS-side
 * code must provide (upstream's own app/IOSCalls.m implements it, built on
 * top of the kernel-exported `async_do_in_workqueue`). That file also pulls
 * in UIKit for clipboard bridging we do not need for a headless `ish
 * <command>`, so this is our own from-scratch implementation of the same
 * documented contract: run `block` on the kernel's single cooperative
 * scheduler thread (the only thread allowed to touch most kernel state —
 * see actuate_kernel()/run_kernel() below) and block the CALLING thread
 * until `block` invokes the `done` continuation it is handed. */
static void ish_sync_do_in_workqueue(void (^block)(void (^done)(void))) {
  __block pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
  __block pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
  __block int finished = 0;
  async_do_in_workqueue(^{
    block(^{
      pthread_mutex_lock(&mutex);
      finished = 1;
      pthread_cond_broadcast(&cond);
      pthread_mutex_unlock(&mutex);
    });
  });
  pthread_mutex_lock(&mutex);
  while (!finished) {
    pthread_cond_wait(&cond, &mutex);
  }
  pthread_mutex_unlock(&mutex);
  pthread_mutex_destroy(&mutex);
  pthread_cond_destroy(&cond);
}

void async_do_in_ios(void (^block)(void)) {
  dispatch_async(dispatch_get_main_queue(), block);
}

static SCNetworkReachabilityRef g_network_reachability;

static void ish_append_dns_text(char *buffer, size_t capacity, size_t *length,
                                const char *format, ...) {
  if (*length >= capacity) {
    return;
  }
  va_list arguments;
  va_start(arguments, format);
  int written = vsnprintf(buffer + *length, capacity - *length, format, arguments);
  va_end(arguments);
  if (written < 0) {
    return;
  }
  size_t remaining = capacity - *length;
  *length += (size_t) written < remaining ? (size_t) written : remaining - 1;
}

/* Upstream iSH performs this in AppDelegate.configureDns(). The HermesLink
 * bridge has no upstream app delegate, so populate the guest resolver directly
 * after its fakefs root is mounted and refresh it whenever iOS network
 * reachability changes. */
static void ish_configure_guest_dns(void) {
  struct __res_state resolver = {0};
  if (res_ninit(&resolver) != 0) {
    ISHLog("ish: could not read the iOS DNS configuration");
    return;
  }

  char resolv_conf[4096] = {0};
  size_t length = 0;
  if (resolver.dnsrch[0] != NULL) {
    ish_append_dns_text(resolv_conf, sizeof(resolv_conf), &length, "search");
    for (int i = 0; resolver.dnsrch[i] != NULL; i++) {
      ish_append_dns_text(resolv_conf, sizeof(resolv_conf), &length, " %s", resolver.dnsrch[i]);
    }
    ish_append_dns_text(resolv_conf, sizeof(resolv_conf), &length, "\n");
  }

  union res_sockaddr_union servers[NI_MAXSERV];
  int server_count = res_getservers(&resolver, servers, NI_MAXSERV);
  char address[NI_MAXHOST];
  for (int i = 0; i < server_count; i++) {
    if (servers[i].sin.sin_len == 0 ||
        getnameinfo((struct sockaddr *) &servers[i].sin, servers[i].sin.sin_len,
                    address, sizeof(address), NULL, 0, NI_NUMERICHOST) != 0) {
      continue;
    }
    ish_append_dns_text(resolv_conf, sizeof(resolv_conf), &length, "nameserver %s\n", address);
  }
  res_ndestroy(&resolver);

  struct task *previous_task = current;
  struct task *init_task = pid_get_task(1);
  if (init_task == NULL) {
    ISHLog("ish: guest init task was unavailable while configuring DNS");
    return;
  }
  current = init_task;
  struct fd *file = generic_open("/etc/resolv.conf", O_WRONLY_ | O_CREAT_ | O_TRUNC_, 0666);
  if (IS_ERR(file)) {
    ISHLog("ish: could not open guest /etc/resolv.conf");
  } else {
    size_t offset = 0;
    while (offset < length) {
      ssize_t written = file->ops->write(file, resolv_conf + offset, length - offset);
      if (written <= 0) {
        ISHLog("ish: could not write guest /etc/resolv.conf");
        break;
      }
      offset += (size_t) written;
    }
    fd_close(file);
  }
  current = previous_task;
}

static void ish_network_reachability_changed(SCNetworkReachabilityRef target,
                                              SCNetworkReachabilityFlags flags,
                                              void *context) {
  (void) target;
  (void) flags;
  (void) context;
  async_do_in_workqueue(^{
    ish_configure_guest_dns();
  });
}

static void ish_start_network_monitor(void) {
  struct sockaddr_in address = {
    .sin_len = sizeof(address),
    .sin_family = AF_INET,
  };
  g_network_reachability =
      SCNetworkReachabilityCreateWithAddress(kCFAllocatorDefault, (struct sockaddr *) &address);
  if (g_network_reachability == NULL ||
      !SCNetworkReachabilitySetCallback(g_network_reachability,
                                        ish_network_reachability_changed, NULL) ||
      !SCNetworkReachabilityScheduleWithRunLoop(g_network_reachability,
                                                CFRunLoopGetMain(), kCFRunLoopCommonModes)) {
    if (g_network_reachability != NULL) {
      SCNetworkReachabilityUnscheduleFromRunLoop(g_network_reachability,
                                                  CFRunLoopGetMain(), kCFRunLoopCommonModes);
      CFRelease(g_network_reachability);
      g_network_reachability = NULL;
    }
    ISHLog("ish: could not start iOS network reachability monitoring");
  }
}

#pragma mark - Diagnostics (ReportPanic / ConsoleLog)

void ReportPanic(const char *message) {
  pthread_mutex_lock(&g_kernel_ready_lock);
  g_kernel_panicked = 1;
  pthread_cond_broadcast(&g_kernel_ready_cond);
  pthread_mutex_unlock(&g_kernel_ready_lock);
  char buffer[256];
  snprintf(buffer, sizeof(buffer), "ish: guest kernel panic: %s", message != NULL ? message : "(no message)");
  ISHLog(buffer);
}

void ConsoleLog(const char *data, unsigned len) {
  unsigned bounded = len > 200 ? 200 : len;
  char buffer[256];
  snprintf(buffer, sizeof(buffer), "ish: console: %.*s", (int) bounded, data != NULL ? data : "");
  ISHLog(buffer);
}

#pragma mark - Clipboard bridge (intentionally unimplemented)

/* app/PasteboardDeviceLinux.c (upstream) is the only caller of these four
 * functions, registering a /dev/clipboard character device during the
 * GUI app's own kernel bootstrap (app/AppDelegate.m), which this glue does
 * not reuse or reproduce: a headless `ish <command>` has no use for guest
 * clipboard access, and skipping that device registration means these
 * never actually run. They exist only so the link succeeds if a future
 * build ever includes that device file. */
long UIPasteboard_changeCount(void) {
  return 0;
}
nsobj_t UIPasteboard_get(void) {
  return NULL;
}
void UIPasteboard_set(const char *data, size_t len) {
  (void) data;
  (void) len;
}
size_t NSData_length(nsobj_t data) {
  (void) data;
  return 0;
}
const void *NSData_bytes(nsobj_t data) {
  (void) data;
  return NULL;
}

#pragma mark - Terminal bridge

/* Our stand-in for upstream's (UIKit/WebKit-backed) Terminal class: just
 * enough state to satisfy the `nsobj_t` contract kernel code expects
 * (opaque, refcounted via objc_get/objc_put, carrying a `struct linux_tty *`
 * set by Terminal_setLinuxTTY) plus the host fd + exit-sentinel scanner a
 * single `ish_run_command()` invocation bridges it to. */
typedef struct ish_terminal {
  _Atomic int refcount;
  int type;
  int number;

  pthread_mutex_t lock; /* guards `tty` and `output_fd` below */
  struct linux_tty *tty;
  int output_fd;
  ish_exit_scanner scanner;

  pthread_mutex_t done_lock;
  pthread_cond_t done_cond;
  int done;
  int have_exit_code;
  int exit_code;

  struct ish_terminal *next;
} ish_terminal;

static pthread_mutex_t g_registry_lock = PTHREAD_MUTEX_INITIALIZER;
static ish_terminal *g_registry = NULL;

static ish_terminal *ish_terminal_create(int type, int number) {
  ish_terminal *term = calloc(1, sizeof(*term));
  term->refcount = 1;
  term->type = type;
  term->number = number;
  term->output_fd = -1;
  pthread_mutex_init(&term->lock, NULL);
  pthread_mutex_init(&term->done_lock, NULL);
  pthread_cond_init(&term->done_cond, NULL);
  ish_exit_scanner_init(&term->scanner);
  return term;
}

static void ish_terminal_signal_done(ish_terminal *term) {
  pthread_mutex_lock(&term->done_lock);
  if (!term->done) {
    term->done = 1;
    pthread_cond_broadcast(&term->done_cond);
  }
  pthread_mutex_unlock(&term->done_lock);
}

nsobj_t Terminal_terminalWithType_number(int type, int number) {
  pthread_mutex_lock(&g_registry_lock);
  for (ish_terminal *t = g_registry; t != NULL; t = t->next) {
    if (t->type == type && t->number == number) {
      atomic_fetch_add(&t->refcount, 1);
      pthread_mutex_unlock(&g_registry_lock);
      return t;
    }
  }
  ish_terminal *term = ish_terminal_create(type, number);
  term->next = g_registry;
  g_registry = term;
  pthread_mutex_unlock(&g_registry_lock);
  return term;
}

nsobj_t objc_get(nsobj_t object) {
  ish_terminal *term = (ish_terminal *) object;
  atomic_fetch_add(&term->refcount, 1);
  return object;
}

void objc_put(nsobj_t object) {
  ish_terminal *term = (ish_terminal *) object;
  if (atomic_fetch_sub(&term->refcount, 1) != 1) {
    return;
  }
  pthread_mutex_lock(&g_registry_lock);
  ish_terminal **link = &g_registry;
  while (*link != NULL && *link != term) {
    link = &(*link)->next;
  }
  if (*link == term) {
    *link = term->next;
  }
  pthread_mutex_unlock(&g_registry_lock);
  /* Never leave an ish_run_command() call blocked forever waiting on a
   * terminal that is being torn down. */
  ish_terminal_signal_done(term);
  pthread_mutex_destroy(&term->lock);
  pthread_mutex_destroy(&term->done_lock);
  pthread_cond_destroy(&term->done_cond);
  free(term);
}

void Terminal_setLinuxTTY(nsobj_t _self, struct linux_tty *tty) {
  ish_terminal *term = (ish_terminal *) _self;
  pthread_mutex_lock(&term->lock);
  term->tty = tty;
  pthread_mutex_unlock(&term->lock);
  if (tty == NULL) {
    /* The guest's pty has fully closed (every reference on the kernel side
     * released it) with no exit sentinel ever observed — the only way that
     * happens is the invoked command replacing the shell via exec(2), or a
     * crash the shell could not trap. Either way, waiting any longer would
     * hang the calling `ish` command forever. */
    ish_terminal_signal_done(term);
  }
}

static void ish_emit_to_fd(void *ctx, const unsigned char *data, size_t len) {
  int fd = *(int *) ctx;
  if (fd < 0 || len == 0) {
    return;
  }
  size_t offset = 0;
  while (offset < len) {
    ssize_t written = write(fd, data + offset, len - offset);
    if (written < 0) {
      if (errno == EINTR) {
        continue;
      }
      break; /* the reader is gone; drop the remainder instead of blocking */
    }
    offset += (size_t) written;
  }
}

int Terminal_sendOutput_length(nsobj_t _self, const char *data, int size) {
  ish_terminal *term = (ish_terminal *) _self;
  pthread_mutex_lock(&term->lock);
  int fd = term->output_fd;
  pthread_mutex_unlock(&term->lock);
  ish_exit_scanner_feed(&term->scanner, (const unsigned char *) data, (size_t) size, ish_emit_to_fd, &fd);
  if (term->scanner.matched) {
    pthread_mutex_lock(&term->done_lock);
    if (!term->done) {
      term->have_exit_code = 1;
      term->exit_code = term->scanner.exit_code;
      term->done = 1;
      pthread_cond_broadcast(&term->done_cond);
    }
    pthread_mutex_unlock(&term->done_lock);
  }
  /* Kernel code (see the pinned app/LinuxPTY.c ios_pty_output_work) treats
   * any short count here as PERMANENTLY DROPPED bytes — it never retries
   * the remainder — so ish_emit_to_fd() above always makes a full,
   * best-effort blocking write and this always reports the whole chunk
   * consumed. */
  return size;
}

int Terminal_roomForOutput(nsobj_t _self) {
  (void) _self;
  return 65536;
}

#pragma mark - Kernel boot (once per app process)

static pthread_once_t g_boot_once = PTHREAD_ONCE_INIT;
static _Atomic int g_boot_result = ISH_RUN_ERR_INVALID_ARGUMENT; /* overwritten by ish_boot_once_body */
static char g_rootfs_path[1024];

const char *DefaultRootPath(void) {
  return g_rootfs_path;
}

void FsInitialize(void) {
  /* Upstream's CurrentRoot.m only performs app-specific version and
   * repository bookkeeping here; HermesLink owns rootfs provisioning. */
  ish_configure_guest_dns();
  async_do_in_ios(^{
    ish_start_network_monitor();
  });
  pthread_mutex_lock(&g_kernel_ready_lock);
  g_kernel_ready = 1;
  pthread_cond_broadcast(&g_kernel_ready_cond);
  pthread_mutex_unlock(&g_kernel_ready_lock);
  ISHLog("ish: guest root filesystem mounted; kernel workqueue is ready");
}

static NSString *ISHRootfsStorageDirectory(void) {
  pthread_mutex_lock(&g_configuration_lock);
  NSString *root = g_configured_root[0] != '\0'
      ? [NSString stringWithUTF8String:g_configured_root]
      : [[NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject
          stringByAppendingPathComponent:@"iSH"] stringByAppendingPathComponent:@"Alpine"];
  pthread_mutex_unlock(&g_configuration_lock);
  if (root == nil) {
    root = [[NSHomeDirectory() stringByAppendingPathComponent:@"Documents/iSH"]
        stringByAppendingPathComponent:@"Alpine"];
  }
  [[NSFileManager defaultManager] createDirectoryAtPath:root withIntermediateDirectories:YES attributes:nil error:nil];
  return root;
}

static BOOL ISHRootfsIsProvisioned(NSString *root) {
  struct stat root_status;
  struct stat database_status;
  struct stat busybox_status;
  struct stat release_status;
  struct stat init_status;
  NSString *data = [root stringByAppendingPathComponent:@"data"];
  NSString *database = [root stringByAppendingPathComponent:@"meta.db"];
  NSString *busybox = [data stringByAppendingPathComponent:@"bin/busybox"];
  NSString *release = [data stringByAppendingPathComponent:@"etc/alpine-release"];
  NSString *init = [data stringByAppendingPathComponent:@"sbin/init"];
  return lstat(root.fileSystemRepresentation, &root_status) == 0 &&
         S_ISDIR(root_status.st_mode) &&
         lstat(database.fileSystemRepresentation, &database_status) == 0 &&
         S_ISREG(database_status.st_mode) &&
         database_status.st_size > 0 &&
         lstat(busybox.fileSystemRepresentation, &busybox_status) == 0 &&
         S_ISREG(busybox_status.st_mode) &&
         lstat(release.fileSystemRepresentation, &release_status) == 0 &&
         S_ISREG(release_status.st_mode) &&
         lstat(init.fileSystemRepresentation, &init_status) == 0 &&
         S_ISREG(init_status.st_mode);
}

static BOOL ISHRootfsHasRawMarkers(NSString *root) {
  NSString *rawRoot = root;
  NSString *busybox = [rawRoot stringByAppendingPathComponent:@"bin/busybox"];
  NSString *release = [rawRoot stringByAppendingPathComponent:@"etc/alpine-release"];
  NSString *init = [rawRoot stringByAppendingPathComponent:@"sbin/init"];
  if (![[NSFileManager defaultManager] fileExistsAtPath:busybox] ||
      ![[NSFileManager defaultManager] fileExistsAtPath:release]) {
    rawRoot = [root stringByAppendingPathComponent:@"data"];
    busybox = [rawRoot stringByAppendingPathComponent:@"bin/busybox"];
    release = [rawRoot stringByAppendingPathComponent:@"etc/alpine-release"];
    init = [rawRoot stringByAppendingPathComponent:@"sbin/init"];
  }
  struct stat busybox_status;
  struct stat release_status;
  struct stat init_status;
  return lstat(busybox.fileSystemRepresentation, &busybox_status) == 0 &&
         (S_ISREG(busybox_status.st_mode) || S_ISLNK(busybox_status.st_mode)) &&
         lstat(release.fileSystemRepresentation, &release_status) == 0 &&
         S_ISREG(release_status.st_mode) &&
         lstat(init.fileSystemRepresentation, &init_status) == 0 &&
         (S_ISREG(init_status.st_mode) || S_ISLNK(init_status.st_mode));
}

int ish_import_rootfs_archive(const char *archive_path, const char *dest_root) {
  if (archive_path == NULL || archive_path[0] == '\0' || dest_root == NULL || dest_root[0] == '\0') {
    return ISH_RUN_ERR_INVALID_ARGUMENT;
  }
  NSString *destination = [NSString stringWithUTF8String:dest_root];
  NSError *error = nil;
  if (![[NSFileManager defaultManager] createDirectoryAtPath:destination
                                 withIntermediateDirectories:NO
                                                  attributes:nil
                                                       error:&error]) {
    return ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
  }
  int status = ish_rootfs_extract(archive_path, dest_root);
  if (status == ISH_ROOTFS_OK) {
    status = ish_rootfs_prepare_fakefs(dest_root);
  }
  if (status != ISH_ROOTFS_OK) {
    return ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
  }
  return ISHRootfsIsProvisioned(destination) ? ISH_RUN_OK : ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
}

/* Extracts the bundled, pinned Alpine rootfs archive (packaged into the app
 * at build time by install_ish_runtime.sh) into writable, persistent app
 * storage on first use. Subsequent launches reuse the same on-disk guest
 * root as-is (this is what makes the guest "persistent": packages the user
 * installs, files they create, etc. survive app relaunches, even though the
 * in-memory kernel/process state does not). */
static int ISHPrepareRootfsIfNeeded(void) {
  NSString *root = ISHRootfsStorageDirectory();
  strlcpy(g_rootfs_path, root.fileSystemRepresentation, sizeof(g_rootfs_path));
  if (ISHRootfsIsProvisioned(root)) {
    int validation = ish_rootfs_prepare_fakefs(root.fileSystemRepresentation);
    if (validation == ISH_ROOTFS_OK) {
      return ISH_RUN_OK;
    }
    ISHLog("ish: the selected rootfs fakefs database is invalid; remove and recreate the profile");
    return ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
  }
  if (ISHRootfsHasRawMarkers(root)) {
    int conversion = ish_rootfs_prepare_fakefs(root.fileSystemRepresentation);
    if (conversion == ISH_ROOTFS_OK && ISHRootfsIsProvisioned(root)) {
      return ISH_RUN_OK;
    }
    char message[256];
    snprintf(message, sizeof(message),
             "ish: could not convert rootfs profile at %s to iSH fakefs format (status %d: %s)",
             root.fileSystemRepresentation, conversion, strerror(errno));
    ISHLog(message);
    return ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
  }
  NSFileManager *fileManager = [NSFileManager defaultManager];
  struct stat rootStatus;
  BOOL rootExists = lstat(root.fileSystemRepresentation, &rootStatus) == 0;
  if (rootExists && !S_ISDIR(rootStatus.st_mode)) {
    ISHLog("ish: the selected rootfs profile is not a real directory; remove and recreate it");
    return ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
  }
  if (rootExists) {
    NSArray<NSString *> *entries = [fileManager contentsOfDirectoryAtPath:root error:nil];
    if (entries == nil || entries.count > 0) {
      ISHLog("ish: the selected rootfs profile is incomplete or incompatible; remove it and import or recreate a valid rootfs");
      return ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
    }
  }
  NSError *directoryError = nil;
  if (!rootExists &&
      ![fileManager createDirectoryAtPath:root withIntermediateDirectories:YES attributes:nil error:&directoryError]) {
    ISHLog([[NSString stringWithFormat:@"ish: could not prepare the selected rootfs profile: %@",
              directoryError.localizedDescription ?: @"unknown filesystem error"] UTF8String]);
    return ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
  }
  NSString *archivePath = [[NSBundle mainBundle] pathForResource:@"ish-rootfs" ofType:@"tar.gz"];
  if (archivePath == nil) {
    ISHLog("ish: bundled rootfs archive (ish-rootfs.tar.gz) is missing from the app bundle");
    return ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
  }
  int status = ish_rootfs_extract(archivePath.fileSystemRepresentation, root.fileSystemRepresentation);
  if (status == ISH_ROOTFS_OK) {
    status = ish_rootfs_prepare_fakefs(root.fileSystemRepresentation);
  }
  if (status != ISH_ROOTFS_OK) {
    char message[256];
    snprintf(message, sizeof(message), "ish: rootfs extraction into %s failed (status %d: %s)",
             root.fileSystemRepresentation, status, strerror(errno));
    ISHLog(message);
    [fileManager removeItemAtPath:root error:nil];
    [fileManager createDirectoryAtPath:root withIntermediateDirectories:YES attributes:nil error:nil];
    return ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
  }
  return ISHRootfsIsProvisioned(root) ? ISH_RUN_OK : ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
}

/* actuate_kernel() calls the pinned upstream run_kernel(), which is the
 * guest's cooperative scheduler loop and, by design, never returns for the
 * life of the process — so it must run on its own permanent, detached
 * thread, started exactly once. */
static void *ish_boot_thread_entry(void *context) {
  (void) context;
#if defined(__APPLE__)
  pthread_setname_np("ish-linux-kernel");
#endif
  ISHLog("ish: entering guest Linux kernel");
  actuate_kernel("");
  return NULL; /* unreachable: actuate_kernel/run_kernel does not return */
}

static void ish_boot_once_body(void) {
  pthread_mutex_lock(&g_configuration_lock);
  g_boot_started = 1;
  pthread_mutex_unlock(&g_configuration_lock);
  int status = ISHPrepareRootfsIfNeeded();
  if (status != ISH_RUN_OK) {
    pthread_mutex_lock(&g_configuration_lock);
    g_boot_started = 0;
    pthread_mutex_unlock(&g_configuration_lock);
    atomic_store(&g_boot_result, status);
    return;
  }
  pthread_t thread;
  pthread_attr_t attr;
  pthread_attr_init(&attr);
  pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
  int created = pthread_create(&thread, &attr, ish_boot_thread_entry, NULL);
  pthread_attr_destroy(&attr);
  if (created != 0) {
    pthread_mutex_lock(&g_configuration_lock);
    g_boot_started = 0;
    pthread_mutex_unlock(&g_configuration_lock);
    ISHLog("ish: failed to start the guest kernel boot thread");
    atomic_store(&g_boot_result, ISH_RUN_ERR_SESSION_START_FAILED);
    return;
  }
  ISHLog("ish: guest Linux kernel boot thread started");
  atomic_store(&g_boot_result, ISH_RUN_OK);
}

int ish_kernel_ensure_booted(void) {
  pthread_once(&g_boot_once, ish_boot_once_body);
  return atomic_load(&g_boot_result);
}

int ish_kernel_has_booted(void) {
  pthread_mutex_lock(&g_configuration_lock);
  int started = g_boot_started;
  pthread_mutex_unlock(&g_configuration_lock);
  return started;
}

/* Workqueue/IRQ submission is unsafe until kernel initialization reaches
 * LinuxRoot.c's rootfs initcall: LinuxInterop.c traps if its host pipe has not
 * yet been created by call_block_init. FsInitialize runs after the guest root
 * is mounted, so it is the first safe readiness signal. */
#define ISH_BOOT_READY_TIMEOUT_SECONDS 30
#define ISH_SESSION_START_ENODEV_RETRIES 2
#define ISH_SESSION_START_RETRY_DELAY_MICROSECONDS 100000

static int ish_wait_for_kernel_ready(void) {
  struct timespec deadline;
  if (clock_gettime(CLOCK_REALTIME, &deadline) != 0) {
    ISHLog("ish: could not read the clock while waiting for kernel startup");
    return ISH_RUN_ERR_BOOT_TIMEOUT;
  }
  deadline.tv_sec += ISH_BOOT_READY_TIMEOUT_SECONDS;

  pthread_mutex_lock(&g_kernel_ready_lock);
  int wait_status = 0;
  while (!g_kernel_ready && !g_kernel_panicked && wait_status == 0) {
    wait_status = pthread_cond_timedwait(&g_kernel_ready_cond, &g_kernel_ready_lock, &deadline);
  }
  int ready = g_kernel_ready;
  int panicked = g_kernel_panicked;
  pthread_mutex_unlock(&g_kernel_ready_lock);

  if (panicked) {
    return ISH_RUN_ERR_KERNEL_PANIC;
  }
  if (!ready) {
    ISHLog("ish: guest kernel was not ready to start a session within the boot timeout");
    return ISH_RUN_ERR_BOOT_TIMEOUT;
  }
  return ISH_RUN_OK;
}

static int ish_mount_documents_on_kernel_thread(const char *documents_path,
                                                const char *mount_path) {
  struct task *previous_task = current;
  struct task *init_task = pid_get_task(1);
  if (init_task == NULL) {
    return -_ESRCH;
  }
  current = init_task;

  char normalized_path[MAX_PATH];
  int error = path_normalize(AT_PWD, mount_path, normalized_path, N_SYMLINK_FOLLOW);
  if (error < 0) {
    goto done;
  }
  if (strcmp(normalized_path, "/") == 0) {
    error = -_EBUSY;
    goto done;
  }

  struct statbuf mount_stat;
  error = generic_statat(AT_PWD, normalized_path, &mount_stat, true);
  if (error < 0) {
    goto done;
  }
  if (!S_ISDIR(mount_stat.mode)) {
    error = -_ENOTDIR;
    goto done;
  }

  lock(&mounts_lock);
  struct mount *existing;
  list_for_each_entry(&mounts, existing, mounts) {
    if (strcmp(existing->point, normalized_path) == 0) {
      error = -_EBUSY;
      unlock(&mounts_lock);
      goto done;
    }
  }
  error = do_mount(&realfs, documents_path, normalized_path, "", 0);
  unlock(&mounts_lock);

done:
  current = previous_task;
  return error;
}

int ish_mount_documents(const char *mount_path, int *mount_error_out) {
  if (mount_error_out != NULL) {
    *mount_error_out = 0;
  }
  if (mount_path == NULL || mount_path[0] == '\0' ||
      strnlen(mount_path, MAX_PATH) >= MAX_PATH || mount_error_out == NULL) {
    return ISH_RUN_ERR_INVALID_ARGUMENT;
  }

  int boot_status = ish_kernel_ensure_booted();
  if (boot_status != ISH_RUN_OK) {
    return boot_status;
  }
  int ready_status = ish_wait_for_kernel_ready();
  if (ready_status != ISH_RUN_OK) {
    return ready_status;
  }

  NSString *documents_path = [NSSearchPathForDirectoriesInDomains(
      NSDocumentDirectory, NSUserDomainMask, YES) firstObject];
  if (documents_path.length == 0) {
    *mount_error_out = -_ENOENT;
    return ISH_RUN_ERR_MOUNT_FAILED;
  }
  NSString *guest_mount_path = [NSString stringWithUTF8String:mount_path];
  if (guest_mount_path == nil) {
    return ISH_RUN_ERR_INVALID_ARGUMENT;
  }

  __block int mount_error = -_EIO;
  ish_sync_do_in_workqueue(^(void (^done)(void)) {
    mount_error = ish_mount_documents_on_kernel_thread(
        documents_path.fileSystemRepresentation, guest_mount_path.UTF8String);
    done();
  });
  if (mount_error < 0) {
    *mount_error_out = mount_error;
    return ISH_RUN_ERR_MOUNT_FAILED;
  }
  return ISH_RUN_OK;
}

#pragma mark - Input forwarding

typedef struct {
  ish_terminal *term;
  int input_fd;
  _Atomic int stop;
} ish_input_forward_context;

static void *ish_input_forward_main(void *arg) {
  ish_input_forward_context *ctx = (ish_input_forward_context *) arg;
  unsigned char buffer[4096];
  for (;;) {
    if (atomic_load(&ctx->stop)) {
      break;
    }
    ssize_t got = read(ctx->input_fd, buffer, sizeof(buffer));
    if (got <= 0) {
      break; /* EOF or error: the host side closed or failed */
    }
    pthread_mutex_lock(&ctx->term->lock);
    int have_tty = ctx->term->tty != NULL;
    pthread_mutex_unlock(&ctx->term->lock);
    if (!have_tty) {
      break;
    }
    __block ssize_t block_len = got;
    __block unsigned char *block_buffer = buffer;
    ish_terminal *term = ctx->term;
    ish_sync_do_in_workqueue(^(void (^done)(void)) {
      pthread_mutex_lock(&term->lock);
      struct linux_tty *tty = term->tty;
      pthread_mutex_unlock(&term->lock);
      if (tty != NULL) {
        tty->ops->send_input(tty, (const char *) block_buffer, (size_t) block_len);
      }
      done();
    });
  }
  objc_put(ctx->term);
  free(ctx);
  return NULL;
}

#pragma mark - Public entry point

int ish_run_command(const char *command, int input_fd, int output_fd, int cols, int rows,
                    int *exit_code_out, int *session_error_out) {
  if (command == NULL || exit_code_out == NULL || session_error_out == NULL) {
    return ISH_RUN_ERR_INVALID_ARGUMENT;
  }
  *exit_code_out = 0;
  *session_error_out = 0;

  int boot_status = ish_kernel_ensure_booted();
  if (boot_status != ISH_RUN_OK) {
    return boot_status;
  }
  int ready_status = ish_wait_for_kernel_ready();
  if (ready_status != ISH_RUN_OK) {
    return ready_status;
  }

  size_t script_size = strlen(command) * 2 + 256;
  char *script = malloc(script_size);
  if (script == NULL) {
    return ISH_RUN_ERR_INVALID_ARGUMENT;
  }
  int written = ish_exit_protocol_wrap_command(command, script, script_size);
  if (written < 0 || (size_t) written >= script_size) {
    free(script);
    return ISH_RUN_ERR_INVALID_ARGUMENT;
  }

  const char *argv_values[] = {"/bin/sh", "-c", script, NULL};
  const char *envp_values[] = {
      "TERM=xterm-256color",
      "HOME=/root",
      "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
      NULL,
  };
  const char **argv = argv_values;
  const char **envp = envp_values;

  __block int start_retval = -1;
  __block nsobj_t start_terminal = NULL;

  /* linux_start_session() must be called from the kernel's own cooperative
   * scheduler thread, exactly like the pinned app/TerminalViewController.m
   * does for its own (interactive) sessions; ish_sync_do_in_workqueue()
   * blocks this calling (ios_system command) thread until that start has
   * actually completed or failed. */
  for (int attempt = 0;; attempt++) {
    start_retval = -1;
    start_terminal = NULL;
    ish_sync_do_in_workqueue(^(void (^done)(void)) {
      linux_start_session(argv[0], argv, envp, ^(int retval, int pid, nsobj_t terminal) {
        (void) pid;
        start_retval = retval;
        start_terminal = terminal;
        done();
      });
    });
    if (start_retval != -ENODEV || start_terminal != NULL ||
        attempt >= ISH_SESSION_START_ENODEV_RETRIES) {
      break;
    }
    ISHLog("ish: guest session startup returned ENODEV; retrying after kernel initialization");
    usleep(ISH_SESSION_START_RETRY_DELAY_MICROSECONDS * (attempt + 1));
  }
  free(script);

  if (start_retval < 0 || start_terminal == NULL) {
    *session_error_out = start_retval;
    char message[160];
    snprintf(message, sizeof(message),
             "ish: guest session startup failed (upstream status %d, terminal %s)",
             start_retval, start_terminal == NULL ? "unavailable" : "available");
    ISHLog(message);
    return ISH_RUN_ERR_SESSION_START_FAILED;
  }

  ish_terminal *term = (ish_terminal *) start_terminal;
  pthread_mutex_lock(&term->lock);
  term->output_fd = output_fd;
  struct linux_tty *tty = term->tty;
  pthread_mutex_unlock(&term->lock);

  if (tty != NULL && (cols > 0 || rows > 0)) {
    ish_sync_do_in_workqueue(^(void (^done)(void)) {
      pthread_mutex_lock(&term->lock);
      struct linux_tty *current_tty = term->tty;
      pthread_mutex_unlock(&term->lock);
      if (current_tty != NULL) {
        current_tty->ops->resize(current_tty, cols, rows);
      }
      done();
    });
  }

  int have_input_thread = 0;
  pthread_t input_thread;
  ish_input_forward_context *input_ctx = NULL;
  if (input_fd >= 0) {
    input_ctx = calloc(1, sizeof(*input_ctx));
    input_ctx->term = term;
    input_ctx->input_fd = input_fd;
    objc_get(start_terminal); /* extra reference owned by the forwarding thread */
    if (pthread_create(&input_thread, NULL, ish_input_forward_main, input_ctx) == 0) {
      have_input_thread = 1;
    } else {
      objc_put(start_terminal);
      free(input_ctx);
      input_ctx = NULL;
    }
  }

  pthread_mutex_lock(&term->done_lock);
  while (!term->done) {
    pthread_cond_wait(&term->done_cond, &term->done_lock);
  }
  int have_exit_code = term->have_exit_code;
  int exit_code = term->exit_code;
  pthread_mutex_unlock(&term->done_lock);

  if (have_input_thread) {
    /* The forwarding thread may still be blocked in read(2) on input_fd;
     * there is no fd we safely own to interrupt that from here, so it is
     * detached and left to exit on its own (next read's EOF/error — which
     * ios_system delivers once this command's stdio pipes are torn down)
     * rather than joined synchronously. */
    atomic_store(&input_ctx->stop, 1);
    pthread_detach(input_thread);
  }

  objc_put(start_terminal); /* release the reference the completion callback handed us */

  if (!have_exit_code) {
    return ISH_RUN_ERR_NO_EXIT_SENTINEL;
  }
  *exit_code_out = exit_code;
  return ISH_RUN_OK;
}
