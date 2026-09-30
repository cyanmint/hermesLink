////////////////////////////////////////////////////////////////////////////////
//
// B L I N K
//
// Copyright (C) 2016-2019 Blink Mobile Shell Project
//
// This file is part of Blink.
//
// Blink is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Blink is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Blink. If not, see <http://www.gnu.org/licenses/>.
//
// In addition, Blink is also subject to certain additional terms under
// GNU GPL version 3 section 7.
//
// You should have received a copy of these additional terms immediately
// following the terms and conditions of the GNU General Public License
// which accompanied the Blink Source Code. If not, see
// <http://www.github.com/blinksh/blink>.
//
////////////////////////////////////////////////////////////////////////////////

#import "AppDelegate.h"
#import "BKiCloudSyncHandler.h"
#import <BlinkConfig/BlinkPaths.h>
#import "BLKDefaults.h"
#import <BlinkConfig/BKHosts.h>
#import <BlinkConfig/BKPubKey.h>
#import <ios_system/ios_system.h>
#import <UserNotifications/UserNotifications.h>
#include <libssh/callbacks.h>
#include "xcall.h"
#include "Blink-Swift.h"
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

#ifdef BLINK_BUILD_ENABLED
extern void build_auto_start_wg_ports(void);
extern void rebind_ports(void);
#endif


@import CloudKit;

static uint16_t HermesReadLE16(const uint8_t *bytes) {
  return (uint16_t)(bytes[0] | ((uint16_t)bytes[1] << 8));
}

static uint32_t HermesReadLE32(const uint8_t *bytes) {
  return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
         ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static BOOL HermesCRCMatches(const uint8_t *bytes, uint32_t length, uint32_t expected) {
  uLong crc = crc32(0L, Z_NULL, 0);
  uint32_t offset = 0;
  while (offset < length) {
    uint32_t chunkLength = MIN((uint32_t)UINT_MAX, length - offset);
    crc = crc32(crc, bytes + offset, (uInt)chunkLength);
    offset += chunkLength;
  }
  return (uint32_t)crc == expected;
}

static int64_t HermesRuntimeTimestamp(NSString *archivePath, BOOL verifyPayloads) {
  NSData *archive = [NSData dataWithContentsOfFile:archivePath
                                           options:NSDataReadingMappedIfSafe
                                             error:nil];
  if (archive.length < 22 || archive.length > UINT32_MAX) {
    return -1;
  }

  const uint8_t *bytes = archive.bytes;
  NSUInteger tailLength = MIN(archive.length, (NSUInteger)(22 + UINT16_MAX));
  NSUInteger tailStart = archive.length - tailLength;
  NSUInteger eocd = NSNotFound;
  for (NSUInteger cursor = tailLength - 22 + 1; cursor > 0;) {
    cursor--;
    const uint8_t *candidate = bytes + tailStart + cursor;
    if (HermesReadLE32(candidate) == 0x06054b50 &&
        cursor + 22 + HermesReadLE16(candidate + 20) == tailLength) {
      eocd = tailStart + cursor;
      break;
    }
  }
  if (eocd == NSNotFound) {
    return -1;
  }

  const uint8_t *endRecord = bytes + eocd;
  uint16_t entriesOnDisk = HermesReadLE16(endRecord + 8);
  uint16_t totalEntries = HermesReadLE16(endRecord + 10);
  uint32_t centralSize = HermesReadLE32(endRecord + 12);
  uint32_t centralOffset = HermesReadLE32(endRecord + 16);
  if (HermesReadLE16(endRecord + 4) != 0 || HermesReadLE16(endRecord + 6) != 0 ||
      entriesOnDisk != totalEntries || totalEntries == UINT16_MAX ||
      centralOffset > eocd || centralSize != eocd - centralOffset) {
    return -1;
  }

  NSUInteger cursor = centralOffset;
  NSUInteger centralEnd = cursor + centralSize;
  NSUInteger timestampCount = 0;
  NSUInteger entryCount = 0;
  int64_t timestampValue = -1;
  NSMutableSet<NSString *> *entryNames = [NSMutableSet setWithCapacity:totalEntries];
  while (cursor < centralEnd) {
    if (centralEnd - cursor < 46 || HermesReadLE32(bytes + cursor) != 0x02014b50) {
      return -1;
    }
    const uint8_t *entry = bytes + cursor;
    uint16_t flags = HermesReadLE16(entry + 8);
    uint16_t method = HermesReadLE16(entry + 10);
    uint32_t crc = HermesReadLE32(entry + 16);
    uint32_t compressedSize = HermesReadLE32(entry + 20);
    uint32_t uncompressedSize = HermesReadLE32(entry + 24);
    uint16_t filenameLength = HermesReadLE16(entry + 28);
    uint16_t extraLength = HermesReadLE16(entry + 30);
    uint16_t commentLength = HermesReadLE16(entry + 32);
    uint32_t localOffset = HermesReadLE32(entry + 42);
    NSUInteger recordLength = 46 + filenameLength + extraLength + commentLength;
    if (recordLength > centralEnd - cursor || filenameLength == 0 ||
        method != 0 || compressedSize != uncompressedSize ||
        (flags & 0x0009) != 0 || localOffset >= centralOffset ||
        centralOffset - localOffset < 30 ||
        HermesReadLE32(bytes + localOffset) != 0x04034b50) {
      return -1;
    }

    NSString *name = [[NSString alloc] initWithBytes:entry + 46
                                               length:filenameLength
                                             encoding:NSUTF8StringEncoding];
    if (name.length == 0 || [entryNames containsObject:name]) {
      return -1;
    }
    [entryNames addObject:name];

    const uint8_t *local = bytes + localOffset;
    uint16_t localNameLength = HermesReadLE16(local + 26);
    uint16_t localExtraLength = HermesReadLE16(local + 28);
    NSUInteger localDataStart = (NSUInteger)localOffset + 30;
    NSUInteger localHeaderRemainder = archive.length - localDataStart;
    if (localNameLength != filenameLength ||
        localNameLength > localHeaderRemainder ||
        localExtraLength > localHeaderRemainder - localNameLength ||
        memcmp(bytes + localDataStart, entry + 46, filenameLength) != 0 ||
        HermesReadLE16(local + 6) != flags || HermesReadLE16(local + 8) != method ||
        HermesReadLE32(local + 14) != crc ||
        HermesReadLE32(local + 18) != compressedSize ||
        HermesReadLE32(local + 22) != uncompressedSize) {
      return -1;
    }

    NSUInteger dataOffset = localDataStart + localNameLength + localExtraLength;
    if (dataOffset > centralOffset || compressedSize > centralOffset - dataOffset) {
      return -1;
    }
    BOOL isTimestamp = [name isEqualToString:@"timestamp.txt"];
    if (isTimestamp) {
      timestampCount++;
      if (timestampCount != 1 || uncompressedSize == 0 || uncompressedSize > 64) {
        return -1;
      }
    }
    if ((verifyPayloads || isTimestamp) &&
        !HermesCRCMatches(bytes + dataOffset, uncompressedSize, crc)) {
      return -1;
    }
    if (isTimestamp) {
      NSString *text = [[NSString alloc] initWithBytes:bytes + dataOffset
                                                length:uncompressedSize
                                              encoding:NSASCIIStringEncoding];
      NSString *trimmed = [text stringByTrimmingCharactersInSet:
        [NSCharacterSet whitespaceAndNewlineCharacterSet]];
      NSCharacterSet *nonDigits = [[NSCharacterSet characterSetWithCharactersInString:@"0123456789"] invertedSet];
      if (trimmed.length == 0 || [trimmed rangeOfCharacterFromSet:nonDigits].location != NSNotFound) {
        return -1;
      }
      unsigned long long parsed = strtoull(trimmed.UTF8String, NULL, 10);
      if (parsed == 0 || parsed > INT64_MAX) {
        return -1;
      }
      timestampValue = (int64_t)parsed;
    }
    cursor += recordLength;
    entryCount++;
  }
  return entryCount == totalEntries && timestampCount == 1 ? timestampValue : -1;
}

static void InstallBundledHermesRuntime(void) {
  NSBundle *bundle = [NSBundle mainBundle];
  NSString *bundledPath = [bundle pathForResource:@"hermesrt" ofType:@"zip"];
  NSString *homePath = [BlinkPaths hermesHomePath];
  NSString *installedPath = [homePath stringByAppendingPathComponent:@"hermesrt.zip"];
  if (bundledPath.length == 0) {
    NSLog(@"Hermes runtime update skipped: bundled hermesrt.zip is missing");
    return;
  }

  int64_t bundledTimestamp = HermesRuntimeTimestamp(bundledPath, NO);
  int64_t installedTimestamp = HermesRuntimeTimestamp(installedPath, YES);
  if (bundledTimestamp <= 0) {
    NSLog(@"Hermes runtime update skipped: bundled timestamp.txt is invalid");
    return;
  }
  if (installedTimestamp >= bundledTimestamp) {
    NSLog(@"Hermes runtime kept: Documents/HermesHome/hermesrt.zip timestamp=%lld bundled=%lld",
          (long long)installedTimestamp, (long long)bundledTimestamp);
    return;
  }

  NSString *temporaryPath = [homePath stringByAppendingPathComponent:
    [NSString stringWithFormat:@"hermesrt.zip.%@.tmp", NSUUID.UUID.UUIDString]];
  NSError *error = nil;
  NSFileManager *fileManager = [NSFileManager defaultManager];
  if (![fileManager copyItemAtPath:bundledPath toPath:temporaryPath error:&error]) {
    [fileManager removeItemAtPath:temporaryPath error:nil];
    NSLog(@"Hermes runtime update failed while staging: %@", error.localizedDescription);
    return;
  }
  if (HermesRuntimeTimestamp(temporaryPath, NO) != bundledTimestamp) {
    [fileManager removeItemAtPath:temporaryPath error:nil];
    NSLog(@"Hermes runtime update failed: staged ZIP timestamp does not match bundle");
    return;
  }
  if (rename(temporaryPath.fileSystemRepresentation, installedPath.fileSystemRepresentation) != 0) {
    int savedErrno = errno;
    [fileManager removeItemAtPath:temporaryPath error:nil];
    NSLog(@"Hermes runtime update failed while replacing archive: %s", strerror(savedErrno));
    return;
  }
  NSLog(@"Hermes runtime installed from IPA: timestamp=%lld", (long long)bundledTimestamp);
}

@interface AppDelegate () <UNUserNotificationCenterDelegate>
@end

@implementation AppDelegate {
  NSTimer *_suspendTimer;
  UIBackgroundTaskIdentifier _suspendTaskId;
  BOOL _suspendedMode;
  BOOL _enforceSuspension;
}
  
void __on_pipebroken_signal(int signum){
  NSLog(@"PIPE is broken");
}

void __setupProcessEnv(void) {
  
  NSBundle *mainBundle = [NSBundle mainBundle];
  int forceOverwrite = 1;
  NSString *SSL_CERT_FILE = [mainBundle pathForResource:@"cacert" ofType:@"pem"];
  setenv("SSL_CERT_FILE", SSL_CERT_FILE.UTF8String, forceOverwrite);
  
  NSString *locales_path = [mainBundle pathForResource:@"locales" ofType:@"bundle"];
  setenv("PATH_LOCALE", locales_path.UTF8String, forceOverwrite);
  setlocale(LC_ALL, "UTF-8");
  setenv("TERM", "xterm-256color", forceOverwrite);
  setenv("LANG", "en_US.UTF-8", forceOverwrite);
  setenv("VIMRUNTIME", [[mainBundle resourcePath] stringByAppendingPathComponent:@"/vim"].UTF8String, 1);
  ssh_threads_set_callbacks(ssh_threads_get_pthread());
  ssh_init();
}

- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)launchOptions {
  HermesLinkAppendLog("application didFinishLaunching");
  
  [Migrator perform];

  [AppDelegate reloadDefaults];
  [[UIView appearance] setTintColor:[UIColor blinkTint]];
  
  signal(SIGPIPE, __on_pipebroken_signal);
 
  dispatch_queue_t bgQueue = dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_BACKGROUND, 0);
  dispatch_async(bgQueue, ^{
    [BlinkPaths linkDocumentsIfNeeded];
    [BlinkPaths linkICloudDriveIfNeeded];
    
  });

  sideLoading = false; // Turn off extra commands from iOS system
  initializeEnvironment(); // initialize environment variables for iOS system
  dispatch_async(bgQueue, ^{
    addCommandList([[NSBundle mainBundle] pathForResource:@"blinkCommandsDictionary" ofType:@"plist"]); // Load blink commands to ios_system
    __setupProcessEnv(); // we should call this after ios_system initializeEnvironment to override its defaults.
    [AppDelegate _loadProfileVars];
  });
  
  // Use the real app Documents directory, which is exposed through Files and
  // file sharing. Do not route Hermes through homePath/Documents: that path is
  // a symlink created asynchronously and can become a private shadow folder.
  NSString *documentsPath = [BlinkPaths documentsPath];
  [[NSFileManager defaultManager] createDirectoryAtPath:documentsPath
                             withIntermediateDirectories:YES
                                              attributes:nil
                                                   error:nil];
  NSString *workspacePath = [documentsPath stringByAppendingPathComponent:@"workspace"];
  [[NSFileManager defaultManager] createDirectoryAtPath:workspacePath
                             withIntermediateDirectories:YES
                                              attributes:nil
                                                   error:nil];
  NSString *hermesHomePath = [BlinkPaths hermesHomePath];
  InstallBundledHermesRuntime();
  NSString *homePath = BlinkPaths.homePath;
  setenv("HOME", homePath.UTF8String, 1);
  setenv("SSH_HOME", homePath.UTF8String, 1);
  setenv("CURL_HOME", homePath.UTF8String, 1);
  setenv("HERMES_HOME", hermesHomePath.UTF8String, 1);
  setenv("HERMES_RUNTIME_ROOT", hermesHomePath.UTF8String, 1);
  setenv("TERMINAL_CWD", workspacePath.UTF8String, 1);
  setenv("PWD", workspacePath.UTF8String, 1);
  
  NSNotificationCenter *nc = NSNotificationCenter.defaultCenter;
  [nc addObserver:self
         selector:@selector(_onSceneDidEnterBackground:)
             name:UISceneDidEnterBackgroundNotification object:nil];
  [nc addObserver:self
           selector:@selector(_onSceneWillEnterForeground:)
               name:UISceneWillEnterForegroundNotification object:nil];
  [nc addObserver:self
         selector:@selector(_onSceneDidActiveNotification:)
             name:UISceneDidActivateNotification object:nil];
  [nc addObserver:self
         selector: @selector(_onScreenConnect)
             name:UIScreenDidConnectNotification object:nil];
  
  [UNUserNotificationCenter currentNotificationCenter].delegate = self;
  
//  [nc addObserver:self selector:@selector(_logEvent:) name:nil object:nil];
//  [nc addObserver:self selector:@selector(_active) name:@"UIApplicationSystemNavigationActionChangedNotification" object:nil];

  [UIApplication sharedApplication].applicationSupportsShakeToEdit = NO;
  
  [_NSFileProviderManager syncWithBKHosts];
  
  [PurchasesUserModelObjc preparePurchasesUserModel];
  
#ifdef BLINK_BUILD_ENABLED
  build_auto_start_wg_ports();
#endif
  
  return YES;
}

//- (void)_active {
//  [[SmarterTermInput shared] realBecomeFirstResponder];
//}
//- (void)_logEvent:(NSNotification *)n {
//  NSLog(@"event, %@, %@", n.name, n.userInfo);
//  if ([n.name isEqualToString:@"UIApplicationSystemNavigationActionChangedNotification"]) {
//    [[SmarterTermInput shared] realBecomeFirstResponder];
//  }
//
//}

+ (void)reloadDefaults {
  [BLKDefaults loadDefaults];
  [BKPubKey loadIDS];
  [BKHosts loadHosts];
  [AppDelegate _loadProfileVars];
}

+ (void)_loadProfileVars {
  NSCharacterSet *whiteSpace = [NSCharacterSet whitespaceCharacterSet];
  NSString *profile = [NSString stringWithContentsOfFile:[BlinkPaths blinkProfileFile] encoding:NSUTF8StringEncoding error:nil];
  [profile enumerateLinesUsingBlock:^(NSString * _Nonnull line, BOOL * _Nonnull stop) {
    NSMutableArray<NSString *> *parts = [[line componentsSeparatedByString:@"="] mutableCopy];
    if (parts.count < 2) {
      return;
    }
    
    NSString *varName = [parts.firstObject stringByTrimmingCharactersInSet:whiteSpace];
    if (varName.length == 0) {
      return;
    }
    [parts removeObjectAtIndex:0];
    NSString *varValue = [[parts componentsJoinedByString:@"="] stringByTrimmingCharactersInSet:whiteSpace];
    if ([varValue hasSuffix:@"\""] || [varValue hasPrefix:@"\""]) {
      NSData *data =  [varValue dataUsingEncoding:NSUTF8StringEncoding];
      varValue = [varValue substringWithRange:NSMakeRange(1, varValue.length - 1)];
      if (data) {
        id value = [NSJSONSerialization JSONObjectWithData:data options:NSJSONReadingAllowFragments error:nil];
        if ([value isKindOfClass:[NSString class]]) {
          varValue = value;
        }
      }
    }
    if (varValue.length == 0) {
      return;
    }
    BOOL forceOverwrite = 1;
    setenv(varName.UTF8String, varValue.UTF8String, forceOverwrite);
  }];
}

- (void)application:(UIApplication *)application didReceiveRemoteNotification:(NSDictionary *)userInfo fetchCompletionHandler:(void (^)(UIBackgroundFetchResult))completionHandler {
  [[BKiCloudSyncHandler sharedHandler]checkForReachabilityAndSync:nil];
  // TODO: pass completion handler.
}

// MARK: NSUserActivity

// Deprecated and no-ops.
// - (BOOL)application:(UIApplication *)application willContinueUserActivityWithType:(NSString *)userActivityType 
// {
//   return YES;
// }

// - (BOOL)application:(UIApplication *)application continueUserActivity:(NSUserActivity *)userActivity restorationHandler:(void (^)(NSArray * _Nullable))restorationHandler
// {
//   return YES;
// }

- (BOOL)application:(UIApplication *)application shouldAllowExtensionPointIdentifier:(NSString *)extensionPointIdentifier {
  if ([extensionPointIdentifier isEqualToString: UIApplicationKeyboardExtensionPointIdentifier]) {
    return ![BLKDefaults disableCustomKeyboards];
  }
  return YES;
}

#pragma mark - State saving and restoring

- (void)applicationProtectedDataWillBecomeUnavailable:(UIApplication *)application
{
  // If a scene is not yet in the background, then await for it to suspend
  NSArray * scenes = UIApplication.sharedApplication.connectedScenes.allObjects;
  for (UIScene *scene in scenes) {
    if (scene.activationState == UISceneActivationStateForegroundActive || scene.activationState == UISceneActivationStateForegroundInactive) {
      _enforceSuspension = true;
      return;
    }
  }

  [self _suspendApplicationOnProtectedDataWillBecomeUnavailable];
}

- (void)applicationWillTerminate:(UIApplication *)application
{
  [self _suspendApplicationOnWillTerminate];
}

- (void)_startMonitoringForSuspending
{
  if (_suspendedMode) {
    return;
  }
  
  UIApplication *application = [UIApplication sharedApplication];
  
  [self _cancelApplicationSuspendTask];
  
  _suspendTaskId = [application beginBackgroundTaskWithName:@"Suspend" expirationHandler:^{
    [self _suspendApplicationWithExpirationHandler];
  }];
  
  NSTimeInterval time = MIN(application.backgroundTimeRemaining * 0.9, 5 * 60);
  [_suspendTimer invalidate];
  _suspendTimer = [NSTimer scheduledTimerWithTimeInterval:time
                                                   target:self
                                                 selector:@selector(_suspendApplicationWithSuspendTimer)
                                                 userInfo:nil
                                                  repeats:NO];
}

- (void)_cancelApplicationSuspendTask {
  [_suspendTimer invalidate];
  if (_suspendTaskId != UIBackgroundTaskInvalid) {
    [[UIApplication sharedApplication] endBackgroundTask:_suspendTaskId];
  }
  _suspendTaskId = UIBackgroundTaskInvalid;
}

- (void)_cancelApplicationSuspend {
  [self _cancelApplicationSuspendTask];
 
  // We can't resume if we don't have access to protected data
  if (UIApplication.sharedApplication.isProtectedDataAvailable) {
    if (_suspendedMode) {
#ifdef BLINK_BUILD_ENABLED
      rebind_ports();
#endif
    }

    _suspendedMode = NO;
  }
}

// Simple wrappers to get the reason of failure from call stack
- (void)_suspendApplicationWithSuspendTimer {
  [self _suspendApplication];
}

- (void)_suspendApplicationWithExpirationHandler {
  [self _suspendApplication];
}

- (void)_suspendApplicationOnWillTerminate {
  [self _suspendApplication];
}

- (void)_suspendApplicationOnProtectedDataWillBecomeUnavailable {
  [self _suspendApplication];
}

- (void)_suspendApplication {
  [_suspendTimer invalidate];

  _enforceSuspension = false;
  
  if (_suspendedMode) {
    return;
  }
  
  [[SessionRegistry shared] suspend];
  _suspendedMode = YES;
  [self _cancelApplicationSuspendTask];
}

#pragma mark - Scenes

- (UISceneConfiguration *) application:(UIApplication *)application
configurationForConnectingSceneSession:(UISceneSession *)connectingSceneSession
                               options:(UISceneConnectionOptions *)options {
  // for (NSUserActivity * activity in options.userActivities) {  }
  return [UISceneConfiguration configurationWithName:@"main"
                                         sessionRole:connectingSceneSession.role];
}



- (void)application:(UIApplication *)application didDiscardSceneSessions:(NSSet<UISceneSession *> *)sceneSessions {
  [SpaceController onDidDiscardSceneSessions: sceneSessions];
}

- (void)_onSceneDidEnterBackground:(NSNotification *)notification {
  NSArray * scenes = UIApplication.sharedApplication.connectedScenes.allObjects;
  for (UIScene *scene in scenes) {
    if (scene.activationState == UISceneActivationStateForegroundActive || scene.activationState == UISceneActivationStateForegroundInactive) {
      return;
    }
  }
  if (_enforceSuspension) {
    [self _suspendApplication];
  } else {
    [self _startMonitoringForSuspending];
  }
}

- (void)_onSceneWillEnterForeground:(NSNotification *)notification {
  [self _cancelApplicationSuspend];
}

- (void)_onSceneDidActiveNotification:(NSNotification *)notification {
  [self _cancelApplicationSuspend];
}

- (void)_onScreenConnect {
  [BLKDefaults applyExternalScreenCompensation:BLKDefaults.overscanCompensation];
}

#pragma mark - UNUserNotificationCenterDelegate

- (void)userNotificationCenter:(UNUserNotificationCenter *)center willPresentNotification:(UNNotification *)notification withCompletionHandler:(void (^)(UNNotificationPresentationOptions))completionHandler {
  UNNotificationPresentationOptions opts = UNNotificationPresentationOptionSound | UNNotificationPresentationOptionList | UNNotificationPresentationOptionBanner | UNNotificationPresentationOptionBadge;
  completionHandler(opts);
}

- (void)userNotificationCenter:(UNUserNotificationCenter *)center didReceiveNotificationResponse:(UNNotificationResponse *)response withCompletionHandler:(void (^)(void))completionHandler {
  SceneDelegate *sceneDelegate = (SceneDelegate *)response.targetScene.delegate;
  
  SpaceController *ctrl = sceneDelegate.spaceController;
  
  [ctrl moveToShellWithKey:response.notification.request.content.threadIdentifier];
  
  completionHandler();
}

#pragma mark - Menu Building

- (void)buildMenuWithBuilder:(id<UIMenuBuilder>)builder {
  if (builder.system == UIMenuSystem.mainSystem) {
    [MenuController buildMenuWith:builder];
  }
}

@end
