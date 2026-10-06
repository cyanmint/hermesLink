#ifndef HERMESLINK_LINUX_XPC_COMPAT_H
#define HERMESLINK_LINUX_XPC_COMPAT_H

#include <stdbool.h>

#ifndef OBJC_BOOL_DEFINED
typedef bool BOOL;
#define OBJC_BOOL_DEFINED 1
#endif

typedef struct _xpc_object_s *xpc_object_t;

#endif
