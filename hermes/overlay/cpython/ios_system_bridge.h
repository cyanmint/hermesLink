/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#ifndef HERMES_IOS_SYSTEM_BRIDGE_H
#define HERMES_IOS_SYSTEM_BRIDGE_H

#if defined(__APPLE__)
#  include <TargetConditionals.h>
#endif

#if defined(TARGET_OS_IPHONE) && TARGET_OS_IPHONE
#  include <dlfcn.h>
#  include <errno.h>
#  include <pthread.h>
#  include <string.h>
#  include <sys/types.h>
#  include <sys/wait.h>

static inline void *hermes_ios_lookup(const char *name)
{
    return dlsym(RTLD_DEFAULT, name);
}

static inline pid_t hermes_ios_fork(void)
{
    typedef pid_t (*ios_fork_fn)(void);
    ios_fork_fn function = (ios_fork_fn)hermes_ios_lookup("ios_fork");
    if (function == NULL) {
        errno = ENOSYS;
        return (pid_t)-1;
    }
    return function();
}

static inline int hermes_ios_subprocess_enabled(char *const envp[])
{
    static const char opt_in[] = "HERMES_IOS_SYSTEM_SUBPROCESS=1";
    if (envp == NULL) {
        return 0;
    }
    for (char *const *item = envp; *item != NULL; ++item) {
        if (strcmp(*item, opt_in) == 0) {
            return 1;
        }
    }
    return 0;
}

static inline int hermes_ios_dup2(int source, int destination)
{
    typedef int (*ios_dup2_fn)(int, int);
    ios_dup2_fn function = (ios_dup2_fn)hermes_ios_lookup("ios_dup2");
    if (function == NULL) {
        errno = ENOSYS;
        return -1;
    }
    return function(source, destination);
}

static inline int hermes_ios_chdir(const char *path)
{
    typedef int (*ios_chdir_fn)(const char *);
    ios_chdir_fn function = (ios_chdir_fn)hermes_ios_lookup("chdir_nolock");
    if (function == NULL) {
        errno = ENOSYS;
        return -1;
    }
    return function(path);
}

static inline int hermes_ios_execv(const char *path, char *const argv[])
{
    typedef int (*ios_execv_fn)(const char *, char *const []);
    ios_execv_fn function = (ios_execv_fn)hermes_ios_lookup("ios_execv");
    if (function == NULL) {
        errno = ENOSYS;
        return -1;
    }
    return function(path, argv);
}

static inline int hermes_ios_execve(const char *path, char *const argv[], char *const envp[])
{
    typedef int (*ios_execve_fn)(const char *, char *const [], char *const []);
    ios_execve_fn function = (ios_execve_fn)hermes_ios_lookup("ios_execve");
    if (function == NULL) {
        errno = ENOSYS;
        return -1;
    }
    return function(path, argv, envp);
}

static inline int hermes_ios_waitpid(pid_t pid, int *status, int options)
{
    typedef pthread_t (*ios_get_thread_fn)(pid_t);
    typedef void (*ios_waitpid_fn)(pid_t);
    typedef int (*ios_status_fn)(void);
    typedef void (*ios_release_fn)(pid_t);

    if (pid <= 0 || (options & ~WNOHANG) != 0) {
        errno = EINVAL;
        return -1;
    }
    ios_get_thread_fn get_thread = (ios_get_thread_fn)hermes_ios_lookup("ios_getThreadId");
    ios_waitpid_fn wait_for_pid = (ios_waitpid_fn)hermes_ios_lookup("ios_waitpid");
    ios_status_fn command_status = (ios_status_fn)hermes_ios_lookup("ios_getCommandStatus");
    ios_release_fn release_pid = (ios_release_fn)hermes_ios_lookup("ios_releaseThreadId");
    if (get_thread == NULL || wait_for_pid == NULL || command_status == NULL) {
        errno = ENOSYS;
        return -1;
    }

    pthread_t thread = get_thread(pid);
    if ((options & WNOHANG) && thread != (pthread_t)0) {
        return 0;
    }
    if (thread != (pthread_t)0) {
        wait_for_pid(pid);
    }
    if (status != NULL) {
        *status = W_EXITCODE(command_status() & 0xff, 0);
    }
    if (release_pid != NULL) {
        release_pid(pid);
    }
    return pid;
}

static inline int hermes_ios_system(const char *command)
{
    typedef int (*ios_system_fn)(const char *);
    ios_system_fn execute = (ios_system_fn)hermes_ios_lookup("ios_system");
    if (execute == NULL) {
        errno = ENOSYS;
        return -1;
    }
    pid_t pid = hermes_ios_fork();
    if (pid == (pid_t)-1) {
        return -1;
    }
    int result = execute(command);
    if (hermes_ios_waitpid(pid, NULL, 0) < 0) {
        return -1;
    }
    return result;
}
#endif /* defined(TARGET_OS_IPHONE) && TARGET_OS_IPHONE */

#endif /* HERMES_IOS_SYSTEM_BRIDGE_H */
