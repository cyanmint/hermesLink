/* HermesLink iSH rootfs profile management. */
#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

FOUNDATION_EXPORT BOOL ISHRootfsProfilesPrepare(NSError **error);
FOUNDATION_EXPORT NSArray<NSString *> * _Nullable ISHRootfsProfileNames(NSError **error);
FOUNDATION_EXPORT NSString * _Nullable ISHRootfsActiveProfileName(NSError **error);
FOUNDATION_EXPORT NSString * _Nullable ISHRootfsActiveProfilePath(NSError **error);
FOUNDATION_EXPORT BOOL ISHRootfsProfileIsValid(NSString *name);
FOUNDATION_EXPORT BOOL ISHRootfsSelectProfile(NSString *name, NSError **error);
FOUNDATION_EXPORT BOOL ISHRootfsCreateProfile(NSString *name, NSError **error);
FOUNDATION_EXPORT BOOL ISHRootfsImportProfile(NSString *name, NSURL *sourceURL, NSError **error);
FOUNDATION_EXPORT BOOL ISHRootfsRenameProfile(NSString *name, NSString *newName, NSError **error);
FOUNDATION_EXPORT BOOL ISHRootfsDeleteProfile(NSString *name, NSError **error);
FOUNDATION_EXPORT NSString *ISHDocumentsHostPath(void);
FOUNDATION_EXPORT BOOL ISHDocumentsAutoMountEnabled(void);
FOUNDATION_EXPORT NSString *ISHDocumentsGuestMountPath(void);
FOUNDATION_EXPORT NSUInteger ISHDocumentsMountMask(void);
FOUNDATION_EXPORT BOOL ISHDocumentsMountConfigure(BOOL enabled,
                                                   NSString *guestPath,
                                                   NSUInteger mask,
                                                   NSError **error);
FOUNDATION_EXPORT BOOL ISHDocumentsMountConfigurationIsCurrent(
    BOOL enabled, NSString *guestPath, NSUInteger mask);

NS_ASSUME_NONNULL_END
