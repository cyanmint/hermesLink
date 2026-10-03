/* HermesLink iSH rootfs profile management. */
#import "ISHRootfsProfiles.h"

#import <BlinkConfig/BlinkPaths.h>
#import "ish_kernel_bridge.h"
#import "ish_rootfs.h"

#include <sys/stat.h>
#include <unistd.h>

static NSString *const ISHDefaultProfileName = @"Alpine";
static NSString *const ISHActiveProfileDefaultsKey = @"HermesLinkISHActiveProfile";
static NSString *const ISHProfilesErrorDomain = @"com.hermeslink.ish-rootfs";
static NSRecursiveLock *ISHProfilesLock;

static NSFileManager *ISHFileManager(void) {
  return NSFileManager.defaultManager;
}

static NSString *ISHDocumentsRoot(void) {
  return [[BlinkPaths documentsPath] stringByAppendingPathComponent:@"iSH"];
}

static NSString *ISHProfilesRoot(void) {
  return [ISHDocumentsRoot() stringByAppendingPathComponent:@"Profiles"];
}

static NSString *ISHProfilePath(NSString *name) {
  return [ISHProfilesRoot() stringByAppendingPathComponent:name];
}

static NSError *ISHProfilesError(NSInteger code, NSString *message) {
  return [NSError errorWithDomain:ISHProfilesErrorDomain
                             code:code
                         userInfo:@{NSLocalizedDescriptionKey: message}];
}

static BOOL ISHSetError(NSError **error, NSInteger code, NSString *message) {
  if (error != NULL) {
    *error = ISHProfilesError(code, message);
  }
  return NO;
}

static BOOL ISHValidProfileName(NSString *name) {
  if (![name isKindOfClass:NSString.class] || name.length == 0 || name.length > 64) {
    return NO;
  }
  NSPredicate *valid = [NSPredicate predicateWithFormat:@"SELF MATCHES %@", @"[A-Za-z0-9][A-Za-z0-9._ -]{0,63}"];
  return [valid evaluateWithObject:name] && ![name isEqualToString:@"."] && ![name isEqualToString:@".."];
}

static BOOL ISHIsDirectoryWithoutFollowingSymlink(NSString *path) {
  struct stat attributes;
  return lstat(path.fileSystemRepresentation, &attributes) == 0 && S_ISDIR(attributes.st_mode);
}

static BOOL ISHPathEntryExists(NSString *path) {
  struct stat attributes;
  return lstat(path.fileSystemRepresentation, &attributes) == 0;
}

static BOOL ISHIsRegularFileWithoutFollowingSymlink(NSString *path) {
  struct stat attributes;
  return lstat(path.fileSystemRepresentation, &attributes) == 0 && S_ISREG(attributes.st_mode);
}

static BOOL ISHRootfsIsValidAtPath(NSString *path) {
  if (!ISHIsDirectoryWithoutFollowingSymlink(path)) {
    return NO;
  }
  NSString *dataPath = [path stringByAppendingPathComponent:@"data"];
  BOOL fakefs = ISHIsRegularFileWithoutFollowingSymlink([path stringByAppendingPathComponent:@"meta.db"]) &&
      ISHIsRegularFileWithoutFollowingSymlink([dataPath stringByAppendingPathComponent:@"bin/busybox"]) &&
      ISHIsRegularFileWithoutFollowingSymlink([dataPath stringByAppendingPathComponent:@"etc/alpine-release"]) &&
      ISHIsRegularFileWithoutFollowingSymlink([dataPath stringByAppendingPathComponent:@"sbin/init"]);
  BOOL raw = ISHIsRegularFileWithoutFollowingSymlink([path stringByAppendingPathComponent:@"bin/busybox"]) &&
      ISHIsRegularFileWithoutFollowingSymlink([path stringByAppendingPathComponent:@"etc/alpine-release"]) &&
      ISHPathEntryExists([path stringByAppendingPathComponent:@"sbin/init"]);
  return fakefs || raw;
}

static void ISHMakeDirectoriesWritable(NSString *path) {
  struct stat attributes;
  if (lstat(path.fileSystemRepresentation, &attributes) != 0 || !S_ISDIR(attributes.st_mode)) {
    return;
  }
  chmod(path.fileSystemRepresentation, 0700);
  NSArray<NSString *> *entries = [ISHFileManager() contentsOfDirectoryAtPath:path error:nil];
  for (NSString *entry in entries) {
    NSString *entryPath = [path stringByAppendingPathComponent:entry];
    if (lstat(entryPath.fileSystemRepresentation, &attributes) == 0 && S_ISDIR(attributes.st_mode)) {
      ISHMakeDirectoriesWritable(entryPath);
    }
  }
}

static void ISHRemoveTemporaryDirectory(NSString *path) {
  if (ISHIsDirectoryWithoutFollowingSymlink(path)) {
    ISHMakeDirectoriesWritable(path);
  }
  [ISHFileManager() removeItemAtPath:path error:nil];
}

static BOOL ISHPrepareLocked(NSError **error) {
  NSFileManager *fm = ISHFileManager();
  NSString *documentsRoot = ISHDocumentsRoot();
  NSString *profilesRoot = ISHProfilesRoot();
  NSError *underlying = nil;
  BOOL documentsRootExists = ISHPathEntryExists(documentsRoot);
  if (documentsRootExists && !ISHIsDirectoryWithoutFollowingSymlink(documentsRoot)) {
    return ISHSetError(error, 12, @"The Documents/iSH profile directory must not be a symbolic link.");
  }
  NSString *legacyBusybox = [documentsRoot stringByAppendingPathComponent:@"bin/busybox"];
  NSString *legacyRelease = [documentsRoot stringByAppendingPathComponent:@"etc/alpine-release"];
  if (documentsRootExists &&
      ISHIsRegularFileWithoutFollowingSymlink(legacyBusybox) &&
      ISHIsRegularFileWithoutFollowingSymlink(legacyRelease)) {
    NSString *documentsDirectory = [documentsRoot stringByDeletingLastPathComponent];
    NSString *stagingPath = [documentsDirectory stringByAppendingPathComponent:
        [NSString stringWithFormat:@".iSH-migration-%@", NSUUID.UUID.UUIDString]];
    if (![fm moveItemAtPath:documentsRoot toPath:stagingPath error:&underlying]) {
      if (error != NULL) {
        *error = underlying;
      }
      return NO;
    }
    BOOL prepared = [fm createDirectoryAtPath:profilesRoot withIntermediateDirectories:YES
                                    attributes:nil error:&underlying];
    if (prepared) {
      prepared = [fm moveItemAtPath:stagingPath toPath:ISHProfilePath(ISHDefaultProfileName)
                              error:&underlying];
    }
    if (!prepared) {
      [fm removeItemAtPath:documentsRoot error:nil];
      if (![fm moveItemAtPath:stagingPath toPath:documentsRoot error:&underlying]) {
        if (error != NULL) {
          *error = underlying;
        }
        return NO;
      }
      if (error != NULL) {
        *error = underlying ?: ISHProfilesError(1, @"Could not migrate the existing Documents/iSH rootfs.");
      }
      return NO;
    }
    [NSUserDefaults.standardUserDefaults setObject:ISHDefaultProfileName forKey:ISHActiveProfileDefaultsKey];
    return YES;
  }

  if (ISHPathEntryExists(profilesRoot) && !ISHIsDirectoryWithoutFollowingSymlink(profilesRoot)) {
    return ISHSetError(error, 12, @"The Documents/iSH profile directory must not be a symbolic link.");
  }
  if (![fm createDirectoryAtPath:profilesRoot withIntermediateDirectories:YES attributes:nil error:&underlying]) {
    if (error != NULL) {
      *error = underlying;
    }
    return NO;
  }
  if (!ISHIsDirectoryWithoutFollowingSymlink(documentsRoot) ||
      !ISHIsDirectoryWithoutFollowingSymlink(profilesRoot)) {
    return ISHSetError(error, 12, @"The Documents/iSH profile directory must not be a symbolic link.");
  }

  NSString *defaultPath = ISHProfilePath(ISHDefaultProfileName);
  if (ISHPathEntryExists(defaultPath) && !ISHIsDirectoryWithoutFollowingSymlink(defaultPath)) {
    return ISHSetError(error, 12, @"The default iSH rootfs profile is not a real directory.");
  }
  if (!ISHPathEntryExists(defaultPath) &&
      ![fm createDirectoryAtPath:defaultPath withIntermediateDirectories:YES attributes:nil error:&underlying]) {
    if (error != NULL) {
      *error = underlying;
    }
    return NO;
  }

  NSString *activeName = [NSUserDefaults.standardUserDefaults stringForKey:ISHActiveProfileDefaultsKey];
  if (!ISHValidProfileName(activeName) || !ISHIsDirectoryWithoutFollowingSymlink(ISHProfilePath(activeName))) {
    [NSUserDefaults.standardUserDefaults setObject:ISHDefaultProfileName forKey:ISHActiveProfileDefaultsKey];
  }
  return YES;
}

static NSArray<NSString *> *ISHProfileNamesLocked(void) {
  NSArray<NSString *> *entries = [ISHFileManager() contentsOfDirectoryAtPath:ISHProfilesRoot() error:nil] ?: @[];
  NSMutableArray<NSString *> *names = [NSMutableArray array];
  for (NSString *entry in entries) {
    if (ISHValidProfileName(entry) && ISHIsDirectoryWithoutFollowingSymlink(ISHProfilePath(entry))) {
      [names addObject:entry];
    }
  }
  [names sortUsingSelector:@selector(localizedCaseInsensitiveCompare:)];
  return names;
}

static BOOL ISHEnsureAvailable(NSError **error) {
  if (ISHProfilesLock == nil) {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
      ISHProfilesLock = [NSRecursiveLock new];
    });
  }
  [ISHProfilesLock lock];
  BOOL prepared = ISHPrepareLocked(error);
  [ISHProfilesLock unlock];
  return prepared;
}

BOOL ISHRootfsProfilesPrepare(NSError **error) {
  return ISHEnsureAvailable(error);
}

NSArray<NSString *> *ISHRootfsProfileNames(NSError **error) {
  if (!ISHEnsureAvailable(error)) {
    return nil;
  }
  [ISHProfilesLock lock];
  NSArray<NSString *> *names = ISHProfileNamesLocked();
  [ISHProfilesLock unlock];
  return names;
}

NSString *ISHRootfsActiveProfileName(NSError **error) {
  if (!ISHEnsureAvailable(error)) {
    return nil;
  }
  [ISHProfilesLock lock];
  NSString *name = [NSUserDefaults.standardUserDefaults stringForKey:ISHActiveProfileDefaultsKey] ?: ISHDefaultProfileName;
  [ISHProfilesLock unlock];
  return name;
}

NSString *ISHRootfsActiveProfilePath(NSError **error) {
  NSString *name = ISHRootfsActiveProfileName(error);
  return name != nil ? ISHProfilePath(name) : nil;
}

BOOL ISHRootfsProfileIsValid(NSString *name) {
  if (!ISHValidProfileName(name) || !ISHEnsureAvailable(nil)) {
    return NO;
  }
  if (!ISHIsDirectoryWithoutFollowingSymlink(ISHProfilePath(name))) {
    return NO;
  }
  return ISHRootfsIsValidAtPath(ISHProfilePath(name));
}

BOOL ISHRootfsSelectProfile(NSString *name, NSError **error) {
  if (!ISHValidProfileName(name)) {
    return ISHSetError(error, 2, @"Profile names must start with a letter or number and contain only letters, numbers, spaces, dots, underscores, or hyphens.");
  }
  if (!ISHEnsureAvailable(error)) {
    return NO;
  }
  [ISHProfilesLock lock];
  BOOL exists = ISHIsDirectoryWithoutFollowingSymlink(ISHProfilePath(name));
  if (exists) {
    [NSUserDefaults.standardUserDefaults setObject:name forKey:ISHActiveProfileDefaultsKey];
  }
  [ISHProfilesLock unlock];
  return exists ? YES : ISHSetError(error, 3, [NSString stringWithFormat:@"No iSH rootfs profile named '%@'.", name]);
}

BOOL ISHRootfsCreateProfile(NSString *name, NSError **error) {
  if (!ISHValidProfileName(name)) {
    return ISHSetError(error, 2, @"Invalid rootfs profile name.");
  }
  if (!ISHEnsureAvailable(error)) {
    return NO;
  }
  [ISHProfilesLock lock];
  NSString *destination = ISHProfilePath(name);
  if ([ISHFileManager() fileExistsAtPath:destination]) {
    [ISHProfilesLock unlock];
    return ISHSetError(error, 4, [NSString stringWithFormat:@"A profile named '%@' already exists.", name]);
  }
  NSString *active = [NSUserDefaults.standardUserDefaults stringForKey:ISHActiveProfileDefaultsKey] ?: ISHDefaultProfileName;
  NSString *source = ISHProfilePath(active);
  NSString *staging = [ISHProfilesRoot() stringByAppendingPathComponent:
      [NSString stringWithFormat:@".create-%@", NSUUID.UUID.UUIDString]];
  NSError *underlying = nil;
  BOOL success = [ISHFileManager() copyItemAtPath:source toPath:staging error:&underlying] &&
                 [ISHFileManager() moveItemAtPath:staging toPath:destination error:&underlying];
  if (!success) {
    ISHRemoveTemporaryDirectory(staging);
  }
  [ISHProfilesLock unlock];
  if (!success) {
    if (error != NULL) {
      *error = underlying ?: ISHProfilesError(5, @"Could not create the rootfs profile.");
    }
  }
  return success;
}

BOOL ISHRootfsImportProfile(NSString *name, NSURL *sourceURL, NSError **error) {
  if (!ISHValidProfileName(name)) {
    return ISHSetError(error, 2, @"Invalid rootfs profile name.");
  }
  if (!ISHEnsureAvailable(error)) {
    return NO;
  }
  [ISHProfilesLock lock];
  NSString *profilesRoot = ISHProfilesRoot();
  NSString *sourcePath = sourceURL.URLByResolvingSymlinksInPath.URLByStandardizingPath.path;
  NSString *resolvedProfilesRoot = [NSURL fileURLWithPath:profilesRoot].URLByResolvingSymlinksInPath.path;
  NSString *managedPrefix = [[resolvedProfilesRoot stringByAppendingString:@"/"] lowercaseString];
  NSString *normalizedSourcePath = sourcePath.lowercaseString;
  if ([normalizedSourcePath isEqualToString:resolvedProfilesRoot.lowercaseString] ||
      [normalizedSourcePath hasPrefix:managedPrefix]) {
    [ISHProfilesLock unlock];
    return ISHSetError(error, 6, @"Import a rootfs from outside Documents/iSH/Profiles.");
  }
  NSString *destination = ISHProfilePath(name);
  if ([ISHFileManager() fileExistsAtPath:destination]) {
    [ISHProfilesLock unlock];
    return ISHSetError(error, 4, [NSString stringWithFormat:@"A profile named '%@' already exists.", name]);
  }
  NSString *staging = [profilesRoot stringByAppendingPathComponent:
      [NSString stringWithFormat:@".import-%@", NSUUID.UUID.UUIDString]];
  NSError *underlying = nil;
  BOOL isDirectory = NO;
  BOOL success = NO;
  if ([ISHFileManager() fileExistsAtPath:sourcePath isDirectory:&isDirectory] && isDirectory) {
    success = [ISHFileManager() copyItemAtPath:sourcePath toPath:staging error:&underlying];
  } else if ([ISHFileManager() fileExistsAtPath:sourcePath]) {
    NSString *extension = sourcePath.pathExtension.lowercaseString;
    NSString *lastComponent = sourcePath.lastPathComponent.lowercaseString;
    if (![extension isEqualToString:@"tgz"] && ![lastComponent hasSuffix:@".tar.gz"]) {
      [ISHProfilesLock unlock];
      return ISHSetError(error, 13, @"Rootfs archives must be gzip-compressed tar files (.tar.gz or .tgz).");
    }
    int status = ish_import_rootfs_archive(sourceURL.fileSystemRepresentation, staging.fileSystemRepresentation);
    if (status == ISH_RUN_OK) {
      success = YES;
    } else {
      underlying = ISHProfilesError(status, [NSString stringWithFormat:@"Could not extract the rootfs archive (status %d).", status]);
    }
  } else {
    underlying = ISHProfilesError(7, @"The selected rootfs source does not exist.");
  }
  if (success && !ISHRootfsIsValidAtPath(staging)) {
    success = NO;
    underlying = ISHProfilesError(8, @"The selected folder or archive does not contain a valid rootfs (expected bin/busybox, etc/alpine-release, and sbin/init).");
  }
  if (success) {
    int status = ish_rootfs_prepare_fakefs(staging.fileSystemRepresentation);
    if (status != ISH_ROOTFS_OK) {
      success = NO;
      underlying = ISHProfilesError(status,
          [NSString stringWithFormat:@"Could not prepare the rootfs for iSH (status %d).", status]);
    }
  }
  if (success) {
    success = [ISHFileManager() moveItemAtPath:staging toPath:destination error:&underlying];
  }
  if (!success) {
    ISHRemoveTemporaryDirectory(staging);
  }
  [ISHProfilesLock unlock];
  if (!success && error != NULL) {
    *error = underlying ?: ISHProfilesError(9, @"Could not import the rootfs profile.");
  }
  return success;
}

BOOL ISHRootfsRenameProfile(NSString *name, NSString *newName, NSError **error) {
  if (!ISHValidProfileName(name) || !ISHValidProfileName(newName)) {
    return ISHSetError(error, 2, @"Invalid rootfs profile name.");
  }
  if (!ISHEnsureAvailable(error)) {
    return NO;
  }
  [ISHProfilesLock lock];
  NSString *source = ISHProfilePath(name);
  NSString *destination = ISHProfilePath(newName);
  BOOL active = [[NSUserDefaults.standardUserDefaults stringForKey:ISHActiveProfileDefaultsKey] isEqualToString:name];
  if (!ISHIsDirectoryWithoutFollowingSymlink(source)) {
    [ISHProfilesLock unlock];
    return ISHSetError(error, 3, [NSString stringWithFormat:@"No iSH rootfs profile named '%@'.", name]);
  }
  if ([name isEqualToString:newName]) {
    [ISHProfilesLock unlock];
    return YES;
  }
  if ([ISHFileManager() fileExistsAtPath:destination]) {
    [ISHProfilesLock unlock];
    return ISHSetError(error, 4, [NSString stringWithFormat:@"A profile named '%@' already exists.", newName]);
  }
  if (active && ish_kernel_has_booted()) {
    [ISHProfilesLock unlock];
    return ISHSetError(error, 10, @"The active rootfs cannot be renamed while the iSH kernel is running. Restart the app after selecting another profile.");
  }
  NSError *underlying = nil;
  BOOL success = [ISHFileManager() moveItemAtPath:source toPath:destination error:&underlying];
  if (success && active) {
    [NSUserDefaults.standardUserDefaults setObject:newName forKey:ISHActiveProfileDefaultsKey];
  }
  [ISHProfilesLock unlock];
  if (!success && error != NULL) {
    *error = underlying;
  }
  return success;
}

BOOL ISHRootfsDeleteProfile(NSString *name, NSError **error) {
  if (!ISHValidProfileName(name)) {
    return ISHSetError(error, 2, @"Invalid rootfs profile name.");
  }
  if (!ISHEnsureAvailable(error)) {
    return NO;
  }
  [ISHProfilesLock lock];
  NSString *path = ISHProfilePath(name);
  NSArray<NSString *> *names = ISHProfileNamesLocked();
  BOOL active = [[NSUserDefaults.standardUserDefaults stringForKey:ISHActiveProfileDefaultsKey] isEqualToString:name];
  if (!ISHIsDirectoryWithoutFollowingSymlink(path)) {
    [ISHProfilesLock unlock];
    return ISHSetError(error, 3, [NSString stringWithFormat:@"No iSH rootfs profile named '%@'.", name]);
  }
  if (active && ish_kernel_has_booted()) {
    [ISHProfilesLock unlock];
    return ISHSetError(error, 10, @"The active rootfs cannot be deleted while the iSH kernel is running. Restart the app after selecting another profile.");
  }
  if (active) {
    NSString *fallback = nil;
    for (NSString *candidate in names) {
      if (![candidate isEqualToString:name]) {
        fallback = candidate;
        break;
      }
    }
    [NSUserDefaults.standardUserDefaults setObject:fallback forKey:ISHActiveProfileDefaultsKey];
  }
  NSError *underlying = nil;
  NSString *staging = [ISHProfilesRoot() stringByAppendingPathComponent:
      [NSString stringWithFormat:@".delete-%@", NSUUID.UUID.UUIDString]];
  if (names.count < 2) {
    BOOL moved = [ISHFileManager() moveItemAtPath:path toPath:staging error:&underlying];
    BOOL recreated = moved &&
        [ISHFileManager() createDirectoryAtPath:path withIntermediateDirectories:NO
                                      attributes:nil error:&underlying];
    if (!recreated) {
      if (moved) {
        [ISHFileManager() moveItemAtPath:staging toPath:path error:nil];
      }
      [ISHProfilesLock unlock];
      if (error != NULL) {
        *error = underlying ?: ISHProfilesError(5, @"Could not reset the only rootfs profile.");
      }
      return NO;
    }
    ISHMakeDirectoriesWritable(staging);
    [ISHFileManager() removeItemAtPath:staging error:nil];
    [NSUserDefaults.standardUserDefaults setObject:name forKey:ISHActiveProfileDefaultsKey];
    [ISHProfilesLock unlock];
    return YES;
  }
  BOOL success = [ISHFileManager() moveItemAtPath:path toPath:staging error:&underlying];
  if (success) {
    ISHMakeDirectoriesWritable(staging);
    success = [ISHFileManager() removeItemAtPath:staging error:&underlying];
    if (!success) {
      [ISHFileManager() moveItemAtPath:staging toPath:path error:nil];
    }
  }
  if (!success && active) {
    [NSUserDefaults.standardUserDefaults setObject:name forKey:ISHActiveProfileDefaultsKey];
  }
  [ISHProfilesLock unlock];
  if (!success && error != NULL) {
    *error = underlying;
  }
  return success;
}
