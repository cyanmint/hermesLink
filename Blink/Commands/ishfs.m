/* HermesLink iSH rootfs profile management command. */
#import <Foundation/Foundation.h>

#import "ios_error.h"
#import "ISHRootfsProfiles.h"
#import "ish_kernel_bridge.h"

#include <stdio.h>
#include <string.h>

static void ishfs_usage(FILE *stream) {
  fprintf(stream,
          "Usage:\n"
          "  ishfs mount-documents [<guest-path>|off]\n"
          "  ishfs list\n"
          "  ishfs create <name>\n"
          "  ishfs import <name> <rootfs-folder-or-tar.gz>\n"
          "  ishfs rename <old-name> <new-name>\n"
          "  ishfs delete <name> --yes\n"
          "  ishfs use <name>\n");
}

static BOOL ishfs_documents_mount_path_is_valid(NSString *path) {
  if (![path hasPrefix:@"/"] || [path isEqualToString:@"/"] || path.length >= 4096) {
    return NO;
  }
  for (NSString *component in [path componentsSeparatedByString:@"/"]) {
    if ([component isEqualToString:@"."] || [component isEqualToString:@".."] ||
        component.length == 0) {
      return NO;
    }
  }
  return YES;
}

static int ishfs_documents_mount(int argc, char *argv[]) {
  NSUserDefaults *defaults = [NSUserDefaults standardUserDefaults];
  NSString *currentPath = [defaults stringForKey:@"HermesLinkISHDocumentsMountPath"];
  if (currentPath == nil) {
    currentPath = @"/mnt/documents";
  }
  if (argc == 2) {
    fprintf(thread_stdout, "%s\n", currentPath.length > 0 ? currentPath.UTF8String : "off");
    return 0;
  }
  if (argc != 3) {
    ishfs_usage(thread_stderr);
    return 2;
  }
  NSString *newPath = [NSString stringWithUTF8String:argv[2]];
  if ([newPath isEqualToString:@"off"]) {
    [defaults setObject:@"" forKey:@"HermesLinkISHDocumentsMountPath"];
    fprintf(thread_stdout,
            "Disabled automatic Documents mounting. The change takes effect after restarting Blink.\n");
    return 0;
  }
  if (!ishfs_documents_mount_path_is_valid(newPath)) {
    fprintf(thread_stderr,
            "ishfs: mount path must be an absolute guest path other than /, without empty, . or .. components\n");
    return 2;
  }
  [defaults setObject:newPath forKey:@"HermesLinkISHDocumentsMountPath"];
  fprintf(thread_stdout,
          "Documents will be mounted at %s after restarting Blink.\n", newPath.UTF8String);
  return 0;
}

static int ishfs_error(NSError *error) {
  fprintf(thread_stderr, "ishfs: %s\n",
          error.localizedDescription.UTF8String ?: "operation failed");
  return 1;
}

__attribute__((visibility("default")))
int ishfs_main(int argc, char *argv[]) {
  NSError *error = nil;
  if (!ISHRootfsProfilesPrepare(&error)) {
    return ishfs_error(error);
  }
  if (argc < 2 || strcmp(argv[1], "help") == 0 || strcmp(argv[1], "--help") == 0) {
    ishfs_usage(argc < 2 ? thread_stderr : thread_stdout);
    return argc < 2 ? 2 : 0;
  }

  if (strcmp(argv[1], "mount-documents") == 0) {
    return ishfs_documents_mount(argc, argv);
  }

  if (strcmp(argv[1], "list") == 0 && argc == 2) {
    NSString *active = ISHRootfsActiveProfileName(&error);
    NSArray<NSString *> *profiles = ISHRootfsProfileNames(&error);
    if (profiles == nil || active == nil) {
      return ishfs_error(error);
    }
    for (NSString *profile in profiles) {
      fprintf(thread_stdout, "%s%s%s\n",
              [profile isEqualToString:active] ? "* " : "  ",
              profile.UTF8String,
              ISHRootfsProfileIsValid(profile) ? "" : " (incomplete rootfs)");
    }
    return 0;
  }

  if (strcmp(argv[1], "create") == 0 && argc == 3) {
    if (!ISHRootfsCreateProfile([NSString stringWithUTF8String:argv[2]], &error)) {
      return ishfs_error(error);
    }
    fprintf(thread_stdout, "Created a copy of the active rootfs as '%s'.\n", argv[2]);
    return 0;
  }

  if (strcmp(argv[1], "import") == 0 && argc == 4) {
    NSURL *source = [NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[3]]];
    if (!ISHRootfsImportProfile([NSString stringWithUTF8String:argv[2]], source, &error)) {
      return ishfs_error(error);
    }
    fprintf(thread_stdout, "Imported rootfs profile '%s'.\n", argv[2]);
    return 0;
  }

  if (strcmp(argv[1], "rename") == 0 && argc == 4) {
    if (!ISHRootfsRenameProfile([NSString stringWithUTF8String:argv[2]],
                                [NSString stringWithUTF8String:argv[3]], &error)) {
      return ishfs_error(error);
    }
    fprintf(thread_stdout, "Renamed rootfs profile '%s' to '%s'.\n", argv[2], argv[3]);
    return 0;
  }

  if (strcmp(argv[1], "delete") == 0 && argc == 4 && strcmp(argv[3], "--yes") == 0) {
    if (!ISHRootfsDeleteProfile([NSString stringWithUTF8String:argv[2]], &error)) {
      return ishfs_error(error);
    }
    fprintf(thread_stdout, "Deleted rootfs profile '%s'.\n", argv[2]);
    return 0;
  }

  if (strcmp(argv[1], "use") == 0 && argc == 3) {
    if (!ISHRootfsSelectProfile([NSString stringWithUTF8String:argv[2]], &error)) {
      return ishfs_error(error);
    }
    fprintf(thread_stdout, "Selected rootfs profile '%s'. If iSH has already run, force-quit and relaunch the app to switch the running kernel.\n",
            argv[2]);
    return 0;
  }

  ishfs_usage(thread_stderr);
  return 2;
}
