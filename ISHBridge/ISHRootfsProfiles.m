/* HermesLink iSH rootfs profile management. */
#import "ISHRootfsProfiles.h"

#import <BlinkConfig/BlinkPaths.h>
#import "ish_kernel_bridge.h"
#import "ish_rootfs.h"

#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static NSString *const ISHDefaultProfileName = @"Alpine";
static NSString *const ISHActiveProfileDefaultsKey = @"HermesLinkISHActiveProfile";
static NSString *const ISHDocumentsAutoMountDefaultsKey = @"HermesLinkISHDocumentsAutoMount";
static NSString *const ISHDocumentsMountPathDefaultsKey = @"HermesLinkISHDocumentsMountPath";
static NSString *const ISHDocumentsMountMaskDefaultsKey = @"HermesLinkISHDocumentsMountMask";
static NSString *const ISHProfilesErrorDomain = @"com.hermeslink.ish-rootfs";
static NSRecursiveLock *ISHProfilesLock;

static NSFileManager *ISHFileManager(void) {
  return NSFileManager.defaultManager;
}

static NSString *ISHDocumentsRoot(void) {
  return [[BlinkPaths documentsPath] stringByAppendingPathComponent:@"iSH"];
}

static BOOL ISHSetError(NSError **error, NSInteger code, NSString *message);
static BOOL ISHValidDocumentsGuestMountPath(NSString *path);

NSString *ISHDocumentsHostPath(void) {
  return BlinkPaths.documentsPath;
}

BOOL ISHDocumentsAutoMountEnabled(void) {
  return [NSUserDefaults.standardUserDefaults boolForKey:ISHDocumentsAutoMountDefaultsKey];
}

NSString *ISHDocumentsGuestMountPath(void) {
  NSString *path = [NSUserDefaults.standardUserDefaults
      stringForKey:ISHDocumentsMountPathDefaultsKey];
  return ISHValidDocumentsGuestMountPath(path) ? path : @"/mnt/documents";
}

NSUInteger ISHDocumentsMountMask(void) {
  NSNumber *mask = [NSUserDefaults.standardUserDefaults
      objectForKey:ISHDocumentsMountMaskDefaultsKey];
  return mask != nil && mask.unsignedIntegerValue <= 0777
      ? mask.unsignedIntegerValue : 0022;
}

static BOOL ISHValidDocumentsGuestMountPath(NSString *path) {
  const char *utf8Path = path.UTF8String;
  if (![path isKindOfClass:NSString.class] || path.length < 2 ||
      utf8Path == NULL || strlen(utf8Path) > 255 ||
      ![path hasPrefix:@"/mnt/"] || [path hasSuffix:@"/"] ||
      [path containsString:@"//"]) {
    return NO;
  }
  for (NSString *component in [path componentsSeparatedByString:@"/"]) {
    if ([component isEqualToString:@"."] || [component isEqualToString:@".."] ||
        component.length > 255) {
      return NO;
    }
    for (NSUInteger index = 0; index < component.length; index++) {
      unichar character = [component characterAtIndex:index];
      if (character < 0x20 || character == 0x7f) {
        return NO;
      }
    }
  }
  return YES;
}

BOOL ISHDocumentsMountConfigure(BOOL enabled, NSString *guestPath,
                               NSUInteger mask, NSError **error) {
  if (!ISHValidDocumentsGuestMountPath(guestPath) || mask > 0777) {
    return ISHSetError(error, 11,
        @"Use a mount path below /mnt and a permission mask from 0000 to 0777.");
  }
  NSUserDefaults *defaults = NSUserDefaults.standardUserDefaults;
  [defaults setBool:enabled forKey:ISHDocumentsAutoMountDefaultsKey];
  [defaults setObject:guestPath forKey:ISHDocumentsMountPathDefaultsKey];
  [defaults setObject:@(mask) forKey:ISHDocumentsMountMaskDefaultsKey];
  return YES;
}

BOOL ISHDocumentsMountConfigurationIsCurrent(BOOL enabled, NSString *guestPath,
                                             NSUInteger mask) {
  NSString *hostPath = enabled ? ISHDocumentsHostPath() : @"";
  const char *hostPathCString = hostPath.UTF8String;
  const char *guestPathCString = guestPath.UTF8String;
  return hostPathCString != NULL && guestPathCString != NULL &&
      ish_documents_configuration_is_current(
          hostPathCString, guestPathCString, (unsigned int) mask) != 0;
}

static NSString *ISHLegacyProfilesRoot(void) {
  return [ISHDocumentsRoot() stringByAppendingPathComponent:@"Profiles"];
}

static NSString *ISHProfilePath(NSString *name) {
  return [ISHDocumentsRoot() stringByAppendingPathComponent:name];
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

static BOOL ISHLegacyProfilesRootContainsProfiles(NSString *path) {
  NSArray<NSString *> *entries = [ISHFileManager() contentsOfDirectoryAtPath:path error:nil];
  if (entries.count == 0) {
    return NO;
  }
  for (NSString *name in entries) {
    NSString *profilePath = [path stringByAppendingPathComponent:name];
    if (!ISHValidProfileName(name) ||
        !ISHIsDirectoryWithoutFollowingSymlink(profilePath) ||
        !ISHRootfsIsValidAtPath(profilePath)) {
      return NO;
    }
  }
  return YES;
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

static BOOL ISHMoveProfiles(NSString *sourceRoot, NSString *destinationRoot,
                           BOOL preserveDuplicateAlpine, NSError **error) {
  NSFileManager *fm = ISHFileManager();
  NSArray<NSString *> *entries = [fm contentsOfDirectoryAtPath:sourceRoot error:error];
  if (entries == nil) {
    return NO;
  }
  NSMutableDictionary<NSString *, NSString *> *destinations = [NSMutableDictionary dictionary];
  for (NSString *name in entries) {
    if (!ISHValidProfileName(name) ||
        !ISHIsDirectoryWithoutFollowingSymlink([sourceRoot stringByAppendingPathComponent:name])) {
      return ISHSetError(error, 1,
          @"Could not safely migrate rootfs profiles because the directory contains unrecognized files.");
    }
    NSString *destinationName = name;
    if (preserveDuplicateAlpine && [name isEqualToString:ISHDefaultProfileName] &&
        ISHPathEntryExists([destinationRoot stringByAppendingPathComponent:name])) {
      destinationName = @"Alpine-legacy";
    }
    NSString *destination = [destinationRoot stringByAppendingPathComponent:destinationName];
    if (ISHPathEntryExists(destination)) {
      return ISHSetError(error, 1,
          [NSString stringWithFormat:@"Could not safely migrate profile '%@' because its destination already exists.",
                                     destinationName]);
    }
    destinations[name] = destinationName;
  }

  NSMutableArray<NSString *> *movedNames = [NSMutableArray array];
  for (NSString *name in entries) {
    NSString *source = [sourceRoot stringByAppendingPathComponent:name];
    NSString *destination = [destinationRoot stringByAppendingPathComponent:destinations[name]];
    NSError *underlying = nil;
    if (![fm moveItemAtPath:source toPath:destination error:&underlying]) {
      for (NSString *movedName in movedNames.reverseObjectEnumerator) {
        NSString *movedSource = [destinationRoot stringByAppendingPathComponent:destinations[movedName]];
        NSString *movedDestination = [sourceRoot stringByAppendingPathComponent:movedName];
        [fm moveItemAtPath:movedSource toPath:movedDestination error:nil];
      }
      if (error != NULL) {
        *error = underlying;
      }
      return NO;
    }
    [movedNames addObject:name];
  }
  if (!ISHDirectoryIsEmpty(sourceRoot)) {
    for (NSString *movedName in movedNames.reverseObjectEnumerator) {
      NSString *movedSource = [destinationRoot stringByAppendingPathComponent:destinations[movedName]];
      NSString *movedDestination = [sourceRoot stringByAppendingPathComponent:movedName];
      [fm moveItemAtPath:movedSource toPath:movedDestination error:nil];
    }
    return ISHSetError(error, 1,
        @"Could not safely finish migrating rootfs profiles because the legacy directory contains unexpected files.");
  }
  if (![fm removeItemAtPath:sourceRoot error:error]) {
    for (NSString *movedName in movedNames.reverseObjectEnumerator) {
      NSString *movedSource = [destinationRoot stringByAppendingPathComponent:destinations[movedName]];
      NSString *movedDestination = [sourceRoot stringByAppendingPathComponent:movedName];
      [fm moveItemAtPath:movedSource toPath:movedDestination error:nil];
    }
    return NO;
  }
  return YES;
}

static BOOL ISHPrepareLocked(NSError **error) {
  NSFileManager *fm = ISHFileManager();
  NSString *documentsRoot = ISHDocumentsRoot();
  NSString *legacyProfilesRoot = ISHLegacyProfilesRoot();
  NSError *underlying = nil;
  BOOL documentsRootExists = ISHPathEntryExists(documentsRoot);
  if (documentsRootExists && !ISHIsDirectoryWithoutFollowingSymlink(documentsRoot)) {
    return ISHSetError(error, 12, @"The Documents/iSH profile directory must not be a symbolic link.");
  }
  if (documentsRootExists && ISHRootfsIsValidAtPath(documentsRoot)) {
    NSString *defaultPath = ISHProfilePath(ISHDefaultProfileName);
    if (ISHPathEntryExists(defaultPath)) {
      return ISHSetError(error, 1,
          @"Could not safely move the existing Documents/iSH rootfs because Documents/iSH/Alpine already exists.");
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
    if (prepared) {
      prepared = [fm moveItemAtPath:stagingPath toPath:defaultPath error:&underlying];
    }
    if (!prepared) {
      if (ISHDirectoryIsEmpty(documentsRoot)) {
        [fm removeItemAtPath:documentsRoot error:nil];
      }
      if (!ISHPathEntryExists(documentsRoot)) {
        [fm moveItemAtPath:stagingPath toPath:documentsRoot error:nil];
      }
      if (error != NULL) {
        *error = underlying ?: ISHProfilesError(1, @"Could not move the existing Documents/iSH rootfs.");
      }
      return NO;
    }
    [NSUserDefaults.standardUserDefaults setObject:ISHDefaultProfileName forKey:ISHActiveProfileDefaultsKey];
  }

  if (ISHPathEntryExists(legacyProfilesRoot) &&
      !ISHIsDirectoryWithoutFollowingSymlink(legacyProfilesRoot)) {
    return ISHSetError(error, 12, @"The legacy Documents/iSH/Profiles path must not be a symbolic link.");
  }
  if (ISHIsDirectoryWithoutFollowingSymlink(legacyProfilesRoot) &&
      !ISHRootfsIsValidAtPath(legacyProfilesRoot) &&
      ISHLegacyProfilesRootContainsProfiles(legacyProfilesRoot) &&
      ISHDirectoryContainsOnlyEntry(documentsRoot, @"Profiles") &&
      !ISHRootfsIsValidAtPath(documentsRoot)) {
    if (!ISHMoveProfiles(legacyProfilesRoot, documentsRoot, YES, error)) {
      return NO;
    }
  }

  NSString *alternateProfilesRoot = [[documentsRoot stringByDeletingLastPathComponent]
      stringByAppendingPathComponent:@"iSH-Profiles"];
  if (ISHPathEntryExists(alternateProfilesRoot) &&
      !ISHIsDirectoryWithoutFollowingSymlink(alternateProfilesRoot)) {
    return ISHSetError(error, 12, @"The legacy Documents/iSH-Profiles path must not be a symbolic link.");
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

  if (ISHIsDirectoryWithoutFollowingSymlink(alternateProfilesRoot) &&
      !ISHMoveProfiles(alternateProfilesRoot, documentsRoot, NO, error)) {
    return NO;
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
  NSArray<NSString *> *entries = [ISHFileManager() contentsOfDirectoryAtPath:ISHDocumentsRoot() error:nil] ?: @[];
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
  NSString *staging = [ISHDocumentsRoot() stringByAppendingPathComponent:
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
  NSString *profilesRoot = ISHDocumentsRoot();
  NSString *sourcePath = sourceURL.URLByResolvingSymlinksInPath.URLByStandardizingPath.path;
  NSString *resolvedManagedRoot = [NSURL fileURLWithPath:ISHDocumentsRoot()].URLByResolvingSymlinksInPath.path;
  NSString *managedRootPrefix = [[resolvedManagedRoot stringByAppendingString:@"/"] lowercaseString];
  NSString *normalizedSourcePath = sourcePath.lowercaseString;
  if ([normalizedSourcePath isEqualToString:resolvedManagedRoot.lowercaseString] ||
      [normalizedSourcePath hasPrefix:managedRootPrefix]) {
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
  if (destinationIsEmptyDefault &&
      ![ISHFileManager() removeItemAtPath:destination error:&underlying]) {
    [ISHProfilesLock unlock];
    if (error != NULL) {
      *error = underlying;
    }
    return NO;
  }
  BOOL success = [ISHFileManager() moveItemAtPath:source toPath:destination error:&underlying];
  if (success && ([name isEqualToString:ISHDefaultProfileName] ||
                  [newName isEqualToString:ISHDefaultProfileName])) {
    success = [ISHFileManager() createDirectoryAtPath:source withIntermediateDirectories:NO
                                             attributes:nil error:&underlying];
    if (!success) {
      [ISHFileManager() moveItemAtPath:destination toPath:source error:nil];
      if (destinationIsEmptyDefault) {
        [ISHFileManager() createDirectoryAtPath:destination withIntermediateDirectories:NO
                                     attributes:nil error:nil];
      }
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
  NSString *staging = [ISHDocumentsRoot() stringByAppendingPathComponent:
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
