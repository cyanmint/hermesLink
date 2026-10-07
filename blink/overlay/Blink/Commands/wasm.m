/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "ios_error.h"

extern NSError *addCommandList(NSString *fileLocation);
extern NSArray *commandsAsArray(void);

static NSArray<NSString *> *HermesWasmCommandCatalog(void) {
  return @[
  @"ctags", @"file", @"funzip", @"json2csv", @"lzmadec", @"lzmainfo",
  @"readtags", @"sqlite3", @"tree", @"unzip", @"xz", @"xzdec", @"zip",
  @"zipcloak", @"zipnote", @"zipsplit"
  ];
}

static NSString *HermesDocumentsPath(void) {
  return NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject;
}

static NSString *HermesArgument(const char *argument) {
  return argument == NULL ? @"" : [NSString stringWithUTF8String:argument];
}

static BOOL HermesPathIsInside(NSString *path, NSString *root) {
  NSString *resolvedPath = [path stringByResolvingSymlinksInPath].stringByStandardizingPath;
  NSString *resolvedRoot = [root stringByResolvingSymlinksInPath].stringByStandardizingPath;
  return [resolvedPath isEqualToString:resolvedRoot] ||
         [resolvedPath hasPrefix:[resolvedRoot stringByAppendingString:@"/"]];
}

static BOOL HermesSafeCommandName(NSString *name) {
  if (name.length == 0 || name.length > 80) return NO;
  NSCharacterSet *allowed = [NSCharacterSet characterSetWithCharactersInString:
    @"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"];
  return [name rangeOfCharacterFromSet:allowed.invertedSet].location == NSNotFound;
}

void HermesLinkRegisterWasmCommands(void) {
  NSString *binPath = [HermesDocumentsPath() stringByAppendingPathComponent:@"bin"];
  NSError *error = nil;
  NSArray<NSString *> *names = [[NSFileManager defaultManager]
    contentsOfDirectoryAtPath:binPath error:&error];
  if (names == nil) return;

  NSMutableSet<NSString *> *existing = [NSMutableSet set];
  for (id command in commandsAsArray() ?: @[]) {
    if ([command isKindOfClass:[NSString class]]) [existing addObject:command];
  }
  NSMutableDictionary<NSString *, NSArray<NSString *> *> *commands = [NSMutableDictionary dictionary];
  for (NSString *filename in names) {
    if (![filename.pathExtension isEqualToString:@"wasm"]) continue;
    NSString *name = [filename stringByDeletingPathExtension];
    NSString *path = [binPath stringByAppendingPathComponent:filename];
    struct stat info;
    if (!HermesSafeCommandName(name) || [existing containsObject:name] ||
        lstat(path.fileSystemRepresentation, &info) != 0 || !S_ISREG(info.st_mode)) {
      continue;
    }
    commands[name] = @[@"MAIN", @"wasm_main", @"", @"no"];
  }
  if (commands.count == 0) return;

  NSData *plist = [NSPropertyListSerialization dataWithPropertyList:commands
    format:NSPropertyListXMLFormat_v1_0 options:0 error:&error];
  if (plist == nil) return;
  NSString *plistPath = [NSTemporaryDirectory()
    stringByAppendingPathComponent:@"hermeslink-wasm-commands.plist"];
  if (![plist writeToFile:plistPath options:NSDataWritingAtomic error:&error]) return;
  addCommandList(plistPath);
}

static NSString *HermesWasmFilePath(NSString *argument, NSString *currentDirectory,
                                    BOOL resolveFromPath) {
  NSFileManager *fileManager = [NSFileManager defaultManager];
  NSMutableArray<NSString *> *candidates = [NSMutableArray array];
  NSString *expanded = [argument stringByExpandingTildeInPath];
  if (expanded.isAbsolutePath) {
    [candidates addObject:expanded];
  } else {
    [candidates addObject:[currentDirectory stringByAppendingPathComponent:expanded]];
    if (resolveFromPath && ![expanded containsString:@"/"]) {
      NSString *binPath = [HermesDocumentsPath() stringByAppendingPathComponent:@"bin"];
      [candidates addObject:[binPath stringByAppendingPathComponent:expanded]];
      if (![expanded.pathExtension isEqualToString:@"wasm"]) {
        [candidates addObject:[[binPath stringByAppendingPathComponent:expanded]
          stringByAppendingPathExtension:@"wasm"]];
      }
      NSString *pathValue = getenv("PATH")
        ? [NSString stringWithUTF8String:getenv("PATH")] : @"";
      NSArray<NSString *> *pathEntries = [pathValue componentsSeparatedByString:@":"];
      for (NSString *entry in pathEntries) {
        if (entry.length == 0) continue;
        [candidates addObject:[entry stringByAppendingPathComponent:expanded]];
        if (![expanded.pathExtension isEqualToString:@"wasm"]) {
          [candidates addObject:[[entry stringByAppendingPathComponent:expanded]
            stringByAppendingPathExtension:@"wasm"]];
        }
      }
    }
  }
  if (![expanded.pathExtension isEqualToString:@"wasm"]) {
    NSArray *originalCandidates = [candidates copy];
    for (NSString *candidate in originalCandidates) {
      [candidates addObject:[candidate stringByAppendingPathExtension:@"wasm"]];
    }
  }
  NSString *documents = HermesDocumentsPath();
  for (NSString *candidate in candidates) {
    NSString *resolved = candidate.stringByStandardizingPath;
    if ([fileManager fileExistsAtPath:resolved] && HermesPathIsInside(resolved, documents)) {
      return resolved;
    }
  }
  return nil;
}

static NSDictionary *HermesWasmFileTree(NSString *root, NSString *excludedPath,
                                        NSError **error) {
  NSFileManager *fileManager = [NSFileManager defaultManager];
  NSMutableArray *directories = [NSMutableArray array];
  NSMutableArray *files = [NSMutableArray array];
  unsigned long long totalBytes = 0;
  NSDirectoryEnumerator *enumerator = [fileManager enumeratorAtURL:
    [NSURL fileURLWithPath:root isDirectory:YES]
    includingPropertiesForKeys:@[NSURLIsDirectoryKey, NSURLIsRegularFileKey, NSURLIsSymbolicLinkKey,
                                 NSURLFileSizeKey]
    options:0 errorHandler:^BOOL(NSURL *url, NSError *enumerationError) {
      if (error) *error = enumerationError;
      return NO;
    }];
  for (NSURL *url in enumerator) {
    NSDictionary *values = [url resourceValuesForKeys:
      @[@"NSURLIsDirectoryKey", @"NSURLIsRegularFileKey", @"NSURLIsSymbolicLinkKey",
        @"NSURLFileSizeKey"] error:error];
    if (values == nil) return nil;
    if ([values[NSURLIsSymbolicLinkKey] boolValue]) {
      [enumerator skipDescendants];
      continue;
    }
    NSString *path = url.path.stringByStandardizingPath;
    if ([path isEqualToString:excludedPath]) continue;
    NSString *relativePath = [path substringFromIndex:root.length + 1];
    if ([values[NSURLIsDirectoryKey] boolValue]) {
      [directories addObject:relativePath];
      continue;
    }
    if (![values[NSURLIsRegularFileKey] boolValue]) continue;
    unsigned long long size = [values[NSURLFileSizeKey] unsignedLongLongValue];
    totalBytes += size;
    if (totalBytes > 16 * 1024 * 1024) {
      if (error) *error = [NSError errorWithDomain:@"HermesLinkWasm"
        code:1 userInfo:@{NSLocalizedDescriptionKey:
          @"The current directory exceeds the 16 MiB WASM filesystem transfer limit."}];
      return nil;
    }
    NSData *data = [NSData dataWithContentsOfURL:url options:0 error:error];
    if (data == nil) return nil;
    [files addObject:@{@"path": relativePath, @"data": data.base64EncodedStringWithOptions:0}];
  }
  return @{@"directories": directories, @"files": files};
}

static NSData *HermesDecodeBase64(id value) {
  if (![value isKindOfClass:[NSString class]]) return nil;
  return [[NSData alloc] initWithBase64EncodedString:value options:0];
}

static BOOL HermesSafeRelativePath(NSString *path) {
  if (![path isKindOfClass:[NSString class]] || path.length == 0 ||
      path.isAbsolutePath || [path containsString:@"\\"] || [path containsString:@"\0"]) {
    return NO;
  }
  for (NSString *part in path.pathComponents) {
    if ([part isEqualToString:@".."] || [part isEqualToString:@"."]) return NO;
  }
  return YES;
}

static BOOL HermesPrepareDirectoryPath(NSString *relativePath, NSString *root) {
  if (relativePath.length == 0) return YES;
  if (!HermesSafeRelativePath(relativePath)) return NO;
  NSFileManager *fileManager = [NSFileManager defaultManager];
  NSString *cursor = root;
  for (NSString *component in relativePath.pathComponents) {
    cursor = [cursor stringByAppendingPathComponent:component];
    NSDictionary *attributes = [fileManager attributesOfItemAtPath:cursor error:nil];
    if (attributes != nil) {
      if (![attributes[NSFileType] isEqualToString:NSFileTypeDirectory]) return NO;
      continue;
    }
    if (![fileManager createDirectoryAtPath:cursor withIntermediateDirectories:NO
                                  attributes:nil error:nil]) return NO;
  }
  return YES;
}

static BOOL HermesApplyWasmFiles(NSDictionary *result, NSDictionary *initialTree,
                                 NSString *workingDirectory) {
  NSFileManager *fileManager = [NSFileManager defaultManager];
  NSMutableSet<NSString *> *written = [NSMutableSet set];
  for (id relativePath in result[@"directories"] ?: @[]) {
    if (!HermesSafeRelativePath(relativePath) ||
        !HermesPrepareDirectoryPath(relativePath, workingDirectory)) return NO;
  }
  for (id entry in result[@"files"] ?: @[]) {
    if (![entry isKindOfClass:[NSDictionary class]]) return NO;
    NSString *relativePath = entry[@"path"];
    NSData *data = HermesDecodeBase64(entry[@"data"]);
    if (data == nil || !HermesSafeRelativePath(relativePath)) return NO;
    NSString *parent = relativePath.stringByDeletingLastPathComponent;
    if ([parent isEqualToString:@"."]) parent = @"";
    if (!HermesPrepareDirectoryPath(parent, workingDirectory)) return NO;
    NSString *destination = [workingDirectory stringByAppendingPathComponent:relativePath];
    if (!HermesPathIsInside(destination, workingDirectory) ||
        ![data writeToFile:destination options:NSDataWritingAtomic error:nil]) return NO;
    [written addObject:relativePath];
  }
  for (NSDictionary *entry in initialTree[@"files"] ?: @[]) {
    NSString *relativePath = entry[@"path"];
    if (![written containsObject:relativePath]) {
      NSString *path = [workingDirectory stringByAppendingPathComponent:relativePath];
      if (HermesPathIsInside(path, workingDirectory)) [fileManager removeItemAtPath:path error:nil];
    }
  }
  return YES;
}

@interface HermesWasmRunner : NSObject <WKScriptMessageHandler, WKNavigationDelegate>
@property(nonatomic, strong) NSCondition *condition;
@property(nonatomic, strong) WKWebView *webView;
@property(nonatomic, strong) NSDictionary *result;
@property(nonatomic, copy) NSString *loadError;
@property(nonatomic) BOOL ready;
@property(nonatomic) BOOL completed;
@property(nonatomic) BOOL busy;
- (NSDictionary *)run:(NSDictionary *)payload error:(NSError **)error;
@end

@implementation HermesWasmRunner

+ (instancetype)sharedRunner {
  static HermesWasmRunner *runner;
  static dispatch_once_t onceToken;
  dispatch_once(&onceToken, ^{
    runner = [HermesWasmRunner new];
    runner.condition = [NSCondition new];
  });
  return runner;
}

- (void)createWebView {
  if (self.webView != nil) return;
  WKWebViewConfiguration *configuration = [WKWebViewConfiguration new];
  WKUserContentController *controller = [WKUserContentController new];
  [controller addScriptMessageHandler:self name:@"hermesWasm"];
  configuration.userContentController = controller;
  self.webView = [[WKWebView alloc] initWithFrame:CGRectMake(0, 0, 1, 1)
                                    configuration:configuration];
  self.webView.navigationDelegate = self;
  self.webView.hidden = YES;
  self.webView.userInteractionEnabled = NO;
  for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) {
    if (![scene isKindOfClass:[UIWindowScene class]]) continue;
    for (UIWindow *window in ((UIWindowScene *)scene).windows) {
      if (window.isKeyWindow) {
        [window.rootViewController.view addSubview:self.webView];
        break;
      }
    }
  }
  NSString *htmlPath = [NSBundle.mainBundle pathForResource:@"index"
    ofType:@"html" inDirectory:@"WasmRuntime"];
  if (htmlPath.length == 0) {
    self.loadError = @"The bundled WebAssembly runtime is missing.";
    return;
  }
  [self.webView loadFileURL:[NSURL fileURLWithPath:htmlPath]
      allowingReadAccessToURL:[NSURL fileURLWithPath:htmlPath.stringByDeletingLastPathComponent
                                      isDirectory:YES]];
}

- (void)userContentController:(WKUserContentController *)userContentController
      didReceiveScriptMessage:(WKScriptMessage *)message {
  if (![message.body isKindOfClass:[NSDictionary class]]) return;
  NSDictionary *body = message.body;
  [self.condition lock];
  if ([body[@"type"] isEqual:@"ready"]) {
    self.ready = YES;
  } else if ([body[@"type"] isEqual:@"finished"]) {
    self.result = body;
    self.completed = YES;
  }
  [self.condition broadcast];
  [self.condition unlock];
}

- (void)webView:(WKWebView *)webView didFailNavigation:(WKNavigation *)navigation
      withError:(NSError *)error {
  [self.condition lock];
  self.loadError = error.localizedDescription;
  [self.condition broadcast];
  [self.condition unlock];
}

- (NSDictionary *)run:(NSDictionary *)payload error:(NSError **)error {
  if (NSThread.isMainThread) {
    if (error) *error = [NSError errorWithDomain:@"HermesLinkWasm" code:1
      userInfo:@{NSLocalizedDescriptionKey:
        @"WASM commands must run outside the iOS main thread."}];
    return nil;
  }
  [self.condition lock];
  while (self.busy) [self.condition wait];
  self.busy = YES;
  self.completed = NO;
  self.result = nil;
  self.loadError = nil;
  [self.condition unlock];

  dispatch_async(dispatch_get_main_queue(), ^{ [self createWebView]; });
  NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:300];
  [self.condition lock];
  while (!self.ready && self.loadError == nil &&
         [self.condition waitUntilDate:deadline]) {}
  if (!self.ready || self.loadError != nil) {
    NSString *message = self.loadError ?: @"Timed out loading the WebAssembly runtime.";
    self.busy = NO;
    [self.condition broadcast];
    [self.condition unlock];
    if (error) *error = [NSError errorWithDomain:@"HermesLinkWasm" code:1
      userInfo:@{NSLocalizedDescriptionKey:message}];
    return nil;
  }
  [self.condition unlock];

  NSError *serializationError = nil;
  NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:0
                                                 error:&serializationError];
  NSString *jsonText = json == nil ? nil : [[NSString alloc]
    initWithData:json encoding:NSUTF8StringEncoding];
  if (jsonText == nil) {
    [self.condition lock];
    self.busy = NO;
    [self.condition broadcast];
    [self.condition unlock];
    if (error) *error = serializationError;
    return nil;
  }
  NSString *script = [NSString stringWithFormat:@"window.runWasm(%@);", jsonText];
  dispatch_async(dispatch_get_main_queue(), ^{
    [self.webView evaluateJavaScript:script completionHandler:^(id value, NSError *evaluationError) {
      if (evaluationError != nil) {
        [self.condition lock];
        self.loadError = evaluationError.localizedDescription;
        self.completed = YES;
        [self.condition broadcast];
        [self.condition unlock];
      }
    }];
  });

  [self.condition lock];
  while (!self.completed && [self.condition waitUntilDate:deadline]) {}
  NSDictionary *result = self.result;
  NSString *message = self.loadError ?: (result == nil
    ? @"Timed out while executing WebAssembly." : nil);
  self.busy = NO;
  [self.condition broadcast];
  [self.condition unlock];
  if (message != nil) {
    if (error) *error = [NSError errorWithDomain:@"HermesLinkWasm" code:1
      userInfo:@{NSLocalizedDescriptionKey:message}];
    return nil;
  }
  return result;
}

@end

static NSData *HermesReadWasmInput(FILE *stream, NSError **error) {
  if (stream == NULL || isatty(fileno(stream))) return [NSData data];
  NSMutableData *input = [NSMutableData data];
  uint8_t buffer[4096];
  size_t count = 0;
  while ((count = fread(buffer, 1, sizeof(buffer), stream)) > 0) {
    if (input.length + count > 4 * 1024 * 1024) {
      if (error) *error = [NSError errorWithDomain:@"HermesLinkWasm" code:1
        userInfo:@{NSLocalizedDescriptionKey:@"WASM standard input exceeds 4 MiB."}];
      return nil;
    }
    [input appendBytes:buffer length:count];
  }
  return input;
}

__attribute__((visibility("default")))
int wasm_main(int argc, char **argv) {
  BOOL wasmSubcommand = argc > 0 &&
    [[HermesArgument(argv[0]) lastPathComponent] isEqualToString:@"wasm"];
  NSString *currentDirectory = [NSFileManager.defaultManager currentDirectoryPath]
    .stringByStandardizingPath;
  NSString *documents = HermesDocumentsPath();
  if (!HermesPathIsInside(currentDirectory, documents)) {
    fprintf(thread_stderr, "wasm: working directory must be inside Documents\n");
    return 126;
  }
  NSString *moduleArgument = wasmSubcommand
    ? (argc > 1 ? HermesArgument(argv[1]) : nil) : HermesArgument(argv[0]);
  BOOL resolveFromPath = !wasmSubcommand;
  if (moduleArgument.length == 0) {
    fprintf(thread_stderr, "usage: wasm <module.wasm> [arguments...]\n");
    return 2;
  }
  NSString *modulePath = HermesWasmFilePath(moduleArgument, currentDirectory, resolveFromPath);
  if (modulePath == nil) {
    fprintf(thread_stderr, "wasm: module not found in Documents: %s\n",
            moduleArgument.UTF8String);
    return 127;
  }
  NSData *module = [NSData dataWithContentsOfFile:modulePath];
  if (module.length < 8 || module.length > 32 * 1024 * 1024 ||
      memcmp(module.bytes, "\0asm\1\0\0\0", 8) != 0) {
    fprintf(thread_stderr, "wasm: invalid WebAssembly v1 module or module exceeds 32 MiB\n");
    return 126;
  }

  NSError *error = nil;
  NSDictionary *tree = HermesWasmFileTree(currentDirectory, modulePath, &error);
  NSData *stdinData = HermesReadWasmInput(thread_stdin, &error);
  if (tree == nil || stdinData == nil) {
    fprintf(thread_stderr, "wasm: %s\n", error.localizedDescription.UTF8String ?: "input error");
    return 1;
  }
  NSMutableArray<NSString *> *arguments = [NSMutableArray array];
  [arguments addObject:modulePath.lastPathComponent];
  int firstArgument = wasmSubcommand ? 2 : 1;
  for (int index = firstArgument; index < argc; ++index) {
    [arguments addObject:HermesArgument(argv[index])];
  }
  NSMutableDictionary *environment = [NSMutableDictionary dictionary];
  [NSProcessInfo.processInfo.environment enumerateKeysAndObjectsUsingBlock:
    ^(NSString *key, NSString *value, BOOL *stop) {
      environment[key] = value;
    }];
  NSMutableDictionary *payload = [@{
    @"module": module.base64EncodedStringWithOptions:0,
    @"args": arguments,
    @"cwd": currentDirectory,
    @"env": environment,
    @"directories": tree[@"directories"],
    @"files": tree[@"files"],
    @"stdin": stdinData.base64EncodedStringWithOptions:0,
  } mutableCopy];
  NSDictionary *result = [[HermesWasmRunner sharedRunner] run:payload error:&error];
  if (result == nil) {
    fprintf(thread_stderr, "wasm: %s\n", error.localizedDescription.UTF8String ?: "runtime error");
    return 1;
  }
  NSData *stdoutData = HermesDecodeBase64(result[@"stdout"]) ?: [NSData data];
  NSData *stderrData = HermesDecodeBase64(result[@"stderr"]) ?: [NSData data];
  if (stdoutData.length > 0) fwrite(stdoutData.bytes, 1, stdoutData.length, thread_stdout);
  if (stderrData.length > 0) fwrite(stderrData.bytes, 1, stderrData.length, thread_stderr);
  NSString *wasmError = result[@"error"];
  if (wasmError.length > 0) fprintf(thread_stderr, "wasm: %s\n", wasmError.UTF8String);
  if (!HermesApplyWasmFiles(result, tree, currentDirectory)) {
    fprintf(thread_stderr, "wasm: unable to safely write WASI filesystem changes\n");
    return 1;
  }
  fflush(thread_stdout);
  fflush(thread_stderr);
  return [result[@"status"] intValue];
}

__attribute__((visibility("default")))
int pkg_main(int argc, char **argv) {
  if (argc == 2 && strcmp(argv[1], "list") == 0) {
    fputs("Available WASI packages:\n", thread_stdout);
    for (NSString *name in HermesWasmCommandCatalog()) {
      fprintf(thread_stdout, "  %s\n", name.UTF8String);
    }
    return 0;
  }
  if (argc != 3 || strcmp(argv[1], "install") != 0) {
    fputs("usage: pkg list | pkg install <package>\n", thread_stderr);
    return 2;
  }
  NSString *name = HermesArgument(argv[2]);
  if (!HermesSafeCommandName(name) ||
      ![[NSSet setWithArray:HermesWasmCommandCatalog()] containsObject:name]) {
    fprintf(thread_stderr, "pkg: unsupported package: %s (use `pkg list`)\n", name.UTF8String);
    return 2;
  }
  NSString *binPath = [HermesDocumentsPath() stringByAppendingPathComponent:@"bin"];
  NSError *error = nil;
  if (![[NSFileManager defaultManager] createDirectoryAtPath:binPath
    withIntermediateDirectories:YES attributes:nil error:&error]) {
    fprintf(thread_stderr, "pkg: %s\n", error.localizedDescription.UTF8String);
    return 1;
  }
  NSString *destination = [[binPath stringByAppendingPathComponent:name]
    stringByAppendingPathExtension:@"wasm"];
  NSString *urlString = [NSString stringWithFormat:
    @"https://github.com/holzschu/a-Shell-commands/releases/download/0.1/%@.wasm", name];
  NSURL *url = [NSURL URLWithString:urlString];
  dispatch_semaphore_t semaphore = dispatch_semaphore_create(0);
  __block NSData *data = nil;
  __block NSHTTPURLResponse *response = nil;
  __block NSError *requestError = nil;
  NSURLSessionConfiguration *configuration = [NSURLSessionConfiguration ephemeralSessionConfiguration];
  configuration.timeoutIntervalForRequest = 120;
  configuration.timeoutIntervalForResource = 180;
  NSURLSession *session = [NSURLSession sessionWithConfiguration:configuration];
  [[session dataTaskWithURL:url completionHandler:^(NSData *downloaded,
      NSURLResponse *received, NSError *receivedError) {
    data = downloaded;
    response = (NSHTTPURLResponse *)received;
    requestError = receivedError;
    dispatch_semaphore_signal(semaphore);
  }] resume];
  if (dispatch_semaphore_wait(semaphore, dispatch_time(DISPATCH_TIME_NOW, 180LL * NSEC_PER_SEC)) != 0) {
    [session invalidateAndCancel];
    fputs("pkg: download timed out\n", thread_stderr);
    return 1;
  }
  [session finishTasksAndInvalidate];
  NSString *host = response.URL.host.lowercaseString;
  NSSet *allowedHosts = [NSSet setWithArray:@[
    @"github.com", @"release-assets.githubusercontent.com", @"objects.githubusercontent.com"
  ]];
  if (requestError != nil || response.statusCode != 200 || data.length < 8 ||
      data.length > 32 * 1024 * 1024 ||
      ![response.URL.scheme.lowercaseString isEqualToString:@"https"] ||
      ![allowedHosts containsObject:host] ||
      memcmp(data.bytes, "\0asm\1\0\0\0", 8) != 0) {
    fprintf(thread_stderr, "pkg: failed to download a valid WASI module%s%s\n",
      requestError == nil ? "" : ": ", requestError.localizedDescription.UTF8String ?: "");
    return 1;
  }
  if (![data writeToFile:destination options:NSDataWritingAtomic error:&error]) {
    fprintf(thread_stderr, "pkg: %s\n", error.localizedDescription.UTF8String);
    return 1;
  }
  HermesLinkRegisterWasmCommands();
  fprintf(thread_stdout, "Installed %s to %s\n", name.UTF8String, destination.UTF8String);
  return 0;
}
