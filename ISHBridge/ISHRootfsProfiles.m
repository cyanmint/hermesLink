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
  return [[BlinkPaths documentsPath] stringByAppendingPathComponent:@"iSH-Profiles"];
}

static NSString *ISHLegacyProfilesRoot(void) {
  return [ISHDocumentsRoot() stringByAppendingPathComponent:@"Profiles"];
}

static NSString *ISHProfilePath(NSString *name) {
  if ([name isEqualToString:ISHDefaultProfileName]) {
    return ISHDocumentsRoot();
  }
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

static BOOL ISHDirectoryIsEmpty(NSString *path) {
  NSArray<NSString *> *entries = [ISHFileManager() contentsOfDirectoryAtPath:path error:nil];
  return entries != nil && entries.count == 0;
}

static BOOL ISHDirectoryContainsOnlyEntry(NSString *path, NSString *entry) {
  NSArray<NSString *> *entries = [ISHFileManager() contentsOfDirectoryAtPath:path error:nil];
  return entries.count == 1 && [entries.firstObject isEqualToString:entry];
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
  NSString *legacyProfilesRoot = ISHLegacyProfilesRoot();
  NSString *legacyDefaultPath = [legacyProfilesRoot stringByAppendingPathComponent:ISHDefaultProfileName];
  NSError *underlying = nil;
  BOOL documentsRootExists = ISHPathEntryExists(documentsRoot);
  if (documentsRootExists && !ISHIsDirectoryWithoutFollowingSymlink(documentsRoot)) {
    return ISHSetError(error, 12, @"The Documents/iSH profile directory must not be a symbolic link.");
  }
  if (documentsRootExists && ISHRootfsIsValidAtPath(legacyDefaultPath) &&
      !ISHRootfsIsValidAtPath(documentsRoot)) {
    if (!ISHDirectoryContainsOnlyEntry(documentsRoot, @"Profiles")) {
      return ISHSetError(error, 1,
          @"Could not safely migrate the existing rootfs because Documents/iSH contains unexpected files.");
    }
    NSString *documentsDirectory = [documentsRoot stringByDeletingLastPathComponent];
    NSString *stagingPath = [documentsDirectory stringByAppendingPathComponent:
        [NSString stringWithFormat:@".iSH-migration-%@", NSUUID.UUID.UUIDString]];
    if (![fm moveItemAtPath:documentsRoot toPath:stagingPath error:&underlying]) {
      if (error != NULL) {
        *error = underlying;
      }
      return NO;
    }
    BOOL prepared = [fm createDirectoryAtPath:documentsRoot withIntermediateDirectories:NO
                                    attributes:nil error:&underlying];
    BOOL defaultMoved = NO;
    if (prepared) {
      NSString *stagedDefault = [[stagingPath stringByAppendingPathComponent:@"Profiles"]
          stringByAppendingPathComponent:ISHDefaultProfileName];
      prepared = [fm moveItemAtPath:stagedDefault toPath:documentsRoot
                              error:&underlying];
      defaultMoved = prepared;
    }
    if (prepared) {
      prepared = [fm createDirectoryAtPath:profilesRoot withIntermediateDirectories:YES
                                 attributes:nil error:&underlying];
    }
    NSString *stagedProfiles = [stagingPath stringByAppendingPathComponent:@"Profiles"];
    NSMutableArray<NSString *> *migratedNames = [NSMutableArray array];
    NSArray<NSString *> *legacyNames = prepared
        ? [fm contentsOfDirectoryAtPath:stagedProfiles error:&underlying] : nil;
    for (NSString *legacyName in legacyNames) {
      if ([legacyName isEqualToString:ISHDefaultProfileName] ||
          !ISHValidProfileName(legacyName)) {
        continue;
      }
      NSString *source = [stagedProfiles stringByAppendingPathComponent:legacyName];
      NSString *destination = [profilesRoot stringByAppendingPathComponent:legacyName];
      if (ISHIsDirectoryWithoutFollowingSymlink(source) &&
          !ISHPathEntryExists(destination) &&
          ![fm moveItemAtPath:source toPath:destination error:&underlying]) {
        prepared = NO;
        break;
      } else if (ISHIsDirectoryWithoutFollowingSymlink(destination) &&
                 !ISHPathEntryExists(source)) {
        [migratedNames addObject:legacyName];
      }
    }
    if (prepared && (!ISHDirectoryIsEmpty(stagedProfiles) ||
                     !ISHDirectoryContainsOnlyEntry(stagingPath, @"Profiles"))) {
      prepared = NO;
      underlying = ISHProfilesError(1,
          @"Could not safely migrate the existing rootfs because the old profile directory contains unexpected files.");
    }
    if (prepared) {
      [fm removeItemAtPath:stagedProfiles error:nil];
    }
    if (!prepared) {
      for (NSString *legacyName in migratedNames.reverseObjectEnumerator) {
        NSString *source = [profilesRoot stringByAppendingPathComponent:legacyName];
        NSString *destination = [stagedProfiles stringByAppendingPathComponent:legacyName];
        [fm moveItemAtPath:source toPath:destination error:nil];
      }
      if (defaultMoved) {
        NSString *stagedDefault = [stagedProfiles stringByAppendingPathComponent:ISHDefaultProfileName];
        [fm moveItemAtPath:documentsRoot toPath:stagedDefault error:nil];
      } else {
        [fm removeItemAtPath:documentsRoot error:nil];
      }
      [fm moveItemAtPath:stagingPath toPath:documentsRoot error:nil];
      if (error != NULL) {
        *error = underlying ?: ISHProfilesError(1, @"Could not migrate the existing Documents/iSH rootfs.");
      }
      return NO;
    }
    ISHRemoveTemporaryDirectory(stagingPath);
    [NSUserDefaults.standardUserDefaults setObject:ISHDefaultProfileName forKey:ISHActiveProfileDefaultsKey];
  }

  if (ISHPathEntryExists(legacyProfilesRoot) &&
      !ISHIsDirectoryWithoutFollowingSymlink(legacyProfilesRoot)) {
    return ISHSetError(error, 12, @"The legacy Documents/iSH/Profiles path must not be a symbolic link.");
  }
  if (ISHIsDirectoryWithoutFollowingSymlink(legacyProfilesRoot) &&
      ISHDirectoryContainsOnlyEntry(documentsRoot, @"Profiles") &&
      !ISHRootfsIsValidAtPath(documentsRoot)) {
    if (ISHPathEntryExists(profilesRoot) &&
        !ISHIsDirectoryWithoutFollowingSymlink(profilesRoot)) {
      return ISHSetError(error, 12, @"The alternate rootfs profile directory must not be a symbolic link.");
    }
    if (![fm createDirectoryAtPath:profilesRoot withIntermediateDirectories:YES
                         attributes:nil error:&underlying]) {
      if (error != NULL) {
        *error = underlying;
      }
      return NO;
    }
    NSArray<NSString *> *legacyNames = [fm contentsOfDirectoryAtPath:legacyProfilesRoot error:nil] ?: @[];
    for (NSString *legacyName in legacyNames) {
      if (!ISHValidProfileName(legacyName)) {
        continue;
      }
      NSString *source = [legacyProfilesRoot stringByAppendingPathComponent:legacyName];
      NSString *destinationName = [legacyName isEqualToString:ISHDefaultProfileName]
          ? @"Alpine-legacy" : legacyName;
      NSString *destination = [profilesRoot stringByAppendingPathComponent:destinationName];
      if (ISHIsDirectoryWithoutFollowingSymlink(source) &&
          !ISHPathEntryExists(destination) &&
          ![fm moveItemAtPath:source toPath:destination error:&underlying]) {
        if (error != NULL) {
          *error = underlying;
        }
        return NO;
      }
    }
    if (!ISHDirectoryIsEmpty(legacyProfilesRoot)) {
      return ISHSetError(error, 1,
          @"Could not safely migrate legacy rootfs profiles because the directory contains unrecognized files.");
    }
    [fm removeItemAtPath:legacyProfilesRoot error:nil];
  }

  if (ISHPathEntryExists(profilesRoot) && !ISHIsDirectoryWithoutFollowingSymlink(profilesRoot)) {
    return ISHSetError(error, 12, @"The Documents/iSH profile directory must not be a symbolic link.");
  }
  if (![fm createDirectoryAtPath:documentsRoot withIntermediateDirectories:YES attributes:nil error:&underlying]) {
    if (error != NULL) {
      *error = underlying;
    }
    return NO;
  }
  if (!ISHIsDirectoryWithoutFollowingSymlink(documentsRoot)) {
    return ISHSetError(error, 12, @"The Documents/iSH profile directory must not be a symbolic link.");
  }

  if (![fm createDirectoryAtPath:profilesRoot withIntermediateDirectories:YES attributes:nil error:&underlying]) {
    if (error != NULL) {
      *error = underlying;
    }
    return NO;
  }
  if (!ISHIsDirectoryWithoutFollowingSymlink(profilesRoot)) {
    return ISHSetError(error, 12, @"The alternate iSH profile directory must not be a symbolic link.");
  }
  NSString *defaultPath = ISHProfilePath(ISHDefaultProfileName);
  if (ISHPathEntryExists(defaultPath) && !ISHIsDirectoryWithoutFollowingSymlink(defaultPath)) {
    return ISHSetError(error, 12, @"The default iSH rootfs is not a real directory.");
  }
  if (!ISHPathEntryExists(defaultPath) &&
      ![fm createDirectoryAtPath:defaultPath withIntermediateDirectories:NO attributes:nil error:&underlying]) {
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
  NSMutableArray<NSString *> *names = [NSMutableArray arrayWithObject:ISHDefaultProfileName];
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
  NSString *resolvedManagedRoot = [NSURL fileURLWithPath:ISHDocumentsRoot()].URLByResolvingSymlinksInPath.path;
  NSString *resolvedProfilesRoot = [NSURL fileURLWithPath:profilesRoot].URLByResolvingSymlinksInPath.path;
  NSString *managedRootPrefix = [[resolvedManagedRoot stringByAppendingString:@"/"] lowercaseString];
  NSString *profilesPrefix = [[resolvedProfilesRoot stringByAppendingString:@"/"] lowercaseString];
  NSString *normalizedSourcePath = sourcePath.lowercaseString;
  if ([normalizedSourcePath isEqualToString:resolvedManagedRoot.lowercaseString] ||
      [normalizedSourcePath hasPrefix:managedRootPrefix] ||
      [normalizedSourcePath isEqualToString:resolvedProfilesRoot.lowercaseString] ||
      [normalizedSourcePath hasPrefix:profilesPrefix]) {
    [ISHProfilesLock unlock];
    return ISHSetError(error, 6, @"Import a rootfs from outside the managed iSH directories.");
  }
  NSString *destination = ISHProfilePath(name);
  BOOL destinationIsEmptyDefault = [name isEqualToString:ISHDefaultProfileName] &&
      ISHIsDirectoryWithoutFollowingSymlink(destination) && ISHDirectoryIsEmpty(destination);
  if ([ISHFileManager() fileExistsAtPath:destination] && !destinationIsEmptyDefault) {
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
    if (destinationIsEmptyDefault) {
      success = [ISHFileManager() removeItemAtPath:destination error:&underlying];
    }
  }
  if (success) {
    success = [ISHFileManager() moveItemAtPath:staging toPath:destination error:&underlying];
    if (!success && destinationIsEmptyDefault &&
        !ISHPathEntryExists(destination)) {
      [ISHFileManager() createDirectoryAtPath:destination withIntermediateDirectories:NO
                                   attributes:nil error:nil];
    }
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
  BOOL destinationIsEmptyDefault = [newName isEqualToString:ISHDefaultProfileName] &&
      ISHIsDirectoryWithoutFollowingSymlink(destination) && ISHDirectoryIsEmpty(destination);
  if ([ISHFileManager() fileExistsAtPath:destination] && !destinationIsEmptyDefault) {
    [ISHProfilesLock unlock];
    return ISHSetError(error, 4, [NSString stringWithFormat:@"A profile named '%@' already exists.", newName]);
  }
  if (active && ish_kernel_has_booted()) {
    [ISHProfilesLock unlock];
    return ISHSetError(error, 10, @"The active rootfs cannot be renamed while the iSH kernel is running. Restart the app after selecting another profile.");
  }
  NSError *underlying = nil;
  if (destinationIsEmptyDefault) {
    [ISHFileManager() removeItemAtPath:destination error:&underlying];
  }
  BOOL success = [ISHFileManager() moveItemAtPath:source toPath:destination error:&underlying];
  if (success && [name isEqualToString:ISHDefaultProfileName]) {
    success = [ISHFileManager() createDirectoryAtPath:source withIntermediateDirectories:NO
                                             attributes:nil error:&underlying];
    if (!success) {
      [ISHFileManager() moveItemAtPath:destination toPath:source error:nil];
    }
  } else if (!success && destinationIsEmptyDefault &&
             !ISHPathEntryExists(destination)) {
    [ISHFileManager() createDirectoryAtPath:destination withIntermediateDirectories:NO
                                 attributes:nil error:nil];
  }
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
