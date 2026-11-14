/* Serialize the original Apple BSD syslog implementation's shared client state.
 */
#include <errno.h>
#include <pthread.h>
#include <stdarg.h>
#include <syslog.h>

extern void commonplace_bsd_openlog(const char *, int, int);
extern void commonplace_bsd_closelog(void);
extern int commonplace_bsd_setlogmask(int);
extern void commonplace_bsd_vsyslog(int, const char *, va_list);
static pthread_mutex_t client_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_once_t client_once = PTHREAD_ONCE_INIT;
static int initialize_error;

static void prepare_fork(void) { pthread_mutex_lock(&client_lock); }
static void finish_fork(void) { pthread_mutex_unlock(&client_lock); }
static void child_fork(void)
{
    /* Waiters in the parent's mutex generation do not exist in this process.
     * Use the same reset as Apple's libc fork handlers. */
    client_lock = (pthread_mutex_t)PTHREAD_MUTEX_INITIALIZER;
}
static void initialize_client(void)
{
    initialize_error = pthread_atfork(prepare_fork, finish_fork, child_fork);
}

static int lock_client(void)
{
    int error = pthread_once(&client_once, initialize_client);
    if (!error)
        error = initialize_error;
    if (!error)
        error = pthread_mutex_lock(&client_lock);
    return error;
}

static void unlock_client(void *unused)
{
    (void)unused;
    pthread_mutex_unlock(&client_lock);
}

void openlog(const char *identity, int options, int facility)
{
    int saved_errno = errno;
    if (lock_client())
        return;
    pthread_cleanup_push(unlock_client, NULL);
    commonplace_bsd_openlog(identity, options, facility);
    pthread_cleanup_pop(1);
    errno = saved_errno;
}

void closelog(void)
{
    int saved_errno = errno;
    if (lock_client())
        return;
    pthread_cleanup_push(unlock_client, NULL);
    commonplace_bsd_closelog();
    pthread_cleanup_pop(1);
    errno = saved_errno;
}

int setlogmask(int mask)
{
    int previous = 0;
    int saved_errno = errno;
    if (lock_client())
        return previous;
    pthread_cleanup_push(unlock_client, NULL);
    previous = commonplace_bsd_setlogmask(mask);
    pthread_cleanup_pop(1);
    errno = saved_errno;
    return previous;
}

void vsyslog(int priority, const char *format, va_list arguments)
{
    int saved_errno = errno;
    if (lock_client())
        return;
    pthread_cleanup_push(unlock_client, NULL);
    errno = saved_errno;
    commonplace_bsd_vsyslog(priority, format, arguments);
    pthread_cleanup_pop(1);
    errno = saved_errno;
}

void syslog(int priority, const char *format, ...)
{
    va_list arguments;
    va_start(arguments, format);
    vsyslog(priority, format, arguments);
    va_end(arguments);
}
