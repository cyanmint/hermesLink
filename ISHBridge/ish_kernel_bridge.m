/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#import <Foundation/Foundation.h>
#import <BlinkConfig/BlinkPaths.h>

/* Pulled from the pinned, unmodified upstream iSH source checkout (see
 * hermes/build/fetch-ish-source.sh / hermes/build/build-ish-static.sh); the
 * header is vendored alongside the prebuilt static libraries this target
 * links against (install_ish_runtime.sh), never copied into this file. */
#include "LinuxInterop.h"

#include "ish_kernel_bridge.h"
#include "ish_rootfs.h"
#include "ish_exit_protocol.h"

#include <dispatch/dispatch.h>
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* Blink/Commands/hermes.m exports this shared diagnostics logger; reusing
 * it keeps iSH's own boot/panic/console noise in the same log a user (or
 * us, during a bug report) already knows to look at. */
extern void HermesLinkAppendLog(const char *message);

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

#pragma mark - Diagnostics (ReportPanic / ConsoleLog)

void ReportPanic(const char *message) {
  char buffer[256];
  snprintf(buffer, sizeof(buffer), "ish: guest kernel panic: %s", message != NULL ? message : "(no message)");
  HermesLinkAppendLog(buffer);
}

void ConsoleLog(const char *data, unsigned len) {
  unsigned bounded = len > 200 ? 200 : len;
  char buffer[256];
  snprintf(buffer, sizeof(buffer), "ish: console: %.*s", (int) bounded, data != NULL ? data : "");
  HermesLinkAppendLog(buffer);
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
}

static NSString *ISHRootfsStorageDirectory(void) {
  NSString *base = [[BlinkPaths blink] stringByAppendingPathComponent:@"ish-root"];
  [[NSFileManager defaultManager] createDirectoryAtPath:base withIntermediateDirectories:YES attributes:nil error:nil];
  return base;
}

static BOOL ISHRootfsIsProvisioned(NSString *root) {
  NSFileManager *fm = [NSFileManager defaultManager];
  return [fm fileExistsAtPath:[root stringByAppendingPathComponent:@"bin/busybox"]] &&
         [fm fileExistsAtPath:[root stringByAppendingPathComponent:@"etc/alpine-release"]];
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
    return ISH_RUN_OK;
  }
  NSString *archivePath = [[NSBundle mainBundle] pathForResource:@"ish-rootfs" ofType:@"tar.gz"];
  if (archivePath == nil) {
    HermesLinkAppendLog("ish: bundled rootfs archive (ish-rootfs.tar.gz) is missing from the app bundle");
    return ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
  }
  int status = ish_rootfs_extract(archivePath.fileSystemRepresentation, root.fileSystemRepresentation);
  if (status != ISH_ROOTFS_OK) {
    char message[192];
    snprintf(message, sizeof(message), "ish: rootfs extraction into %s failed (status %d)",
             root.fileSystemRepresentation, status);
    HermesLinkAppendLog(message);
    return ISH_RUN_ERR_ROOTFS_EXTRACT_FAILED;
  }
  return ISH_RUN_OK;
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
  actuate_kernel("");
  return NULL; /* unreachable: actuate_kernel/run_kernel does not return */
}

static void ish_boot_once_body(void) {
  int status = ISHPrepareRootfsIfNeeded();
  if (status != ISH_RUN_OK) {
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
    HermesLinkAppendLog("ish: failed to start the guest kernel boot thread");
    atomic_store(&g_boot_result, ISH_RUN_ERR_SESSION_START_FAILED);
    return;
  }
  HermesLinkAppendLog("ish: guest Linux kernel boot thread started");
  atomic_store(&g_boot_result, ISH_RUN_OK);
}

int ish_kernel_ensure_booted(void) {
  pthread_once(&g_boot_once, ish_boot_once_body);
  return atomic_load(&g_boot_result);
}

/* ish_kernel_ensure_booted() only starts the kernel's boot thread; it does
 * not (cannot, cheaply) know when the kernel has initialized far enough to
 * safely accept work (workqueue/IRQ plumbing, devpts mount, fakefs mount —
 * see the pinned app/LinuxRoot.c `ish_rootfs` initcall this bridge's own
 * DefaultRootPath() feeds). Rather than guess a fixed sleep, this probes
 * readiness with the exact mechanism a real session start would use
 * (`ish_sync_do_in_workqueue`), bounded by a timeout so a kernel that is
 * slow — or, in the worst case, stuck — fails the calling `ish` command
 * clearly instead of hanging it (and the UI thread behind it) forever.
 * Successful readiness is cached forever; a timeout is retried on the next
 * call, since a slow (not stuck) boot is the more likely real-world case. */
#define ISH_BOOT_READY_TIMEOUT_SECONDS 30

static pthread_mutex_t g_ready_lock = PTHREAD_MUTEX_INITIALIZER;
static int g_ready = 0;

static int ish_wait_for_kernel_ready(void) {
  pthread_mutex_lock(&g_ready_lock);
  if (g_ready) {
    pthread_mutex_unlock(&g_ready_lock);
    return ISH_RUN_OK;
  }
  pthread_mutex_unlock(&g_ready_lock);

  dispatch_semaphore_t probe_done = dispatch_semaphore_create(0);
  dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
    ish_sync_do_in_workqueue(^(void (^done)(void)) {
      done();
    });
    dispatch_semaphore_signal(probe_done);
  });
  dispatch_time_t deadline = dispatch_time(DISPATCH_TIME_NOW, (int64_t) ISH_BOOT_READY_TIMEOUT_SECONDS * NSEC_PER_SEC);
  long timed_out = dispatch_semaphore_wait(probe_done, deadline);
  if (timed_out != 0) {
    HermesLinkAppendLog("ish: guest kernel was not ready to start a session within the boot timeout");
    return ISH_RUN_ERR_BOOT_TIMEOUT;
  }
  pthread_mutex_lock(&g_ready_lock);
  g_ready = 1;
  pthread_mutex_unlock(&g_ready_lock);
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

int ish_run_command(const char *command, int input_fd, int output_fd, int cols, int rows, int *exit_code_out) {
  if (command == NULL || exit_code_out == NULL) {
    return ISH_RUN_ERR_INVALID_ARGUMENT;
  }
  *exit_code_out = 0;

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

  const char *argv[] = {"/bin/sh", "-c", script, NULL};
  const char *envp[] = {
      "TERM=xterm-256color",
      "HOME=/root",
      "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
      NULL,
  };

  __block int start_retval = -1;
  __block nsobj_t start_terminal = NULL;

  /* linux_start_session() must be called from the kernel's own cooperative
   * scheduler thread, exactly like the pinned app/TerminalViewController.m
   * does for its own (interactive) sessions; ish_sync_do_in_workqueue()
   * blocks this calling (ios_system command) thread until that start has
   * actually completed or failed. */
  ish_sync_do_in_workqueue(^(void (^done)(void)) {
    linux_start_session(argv[0], argv, envp, ^(int retval, int pid, nsobj_t terminal) {
      (void) pid;
      start_retval = retval;
      start_terminal = terminal;
      done();
    });
  });
  free(script);

  if (start_retval < 0 || start_terminal == NULL) {
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
