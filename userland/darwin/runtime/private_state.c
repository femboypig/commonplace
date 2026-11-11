#include "profile.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>

static void *values[768];
static unsigned char keys[768];

int commonplace_libc_once(pthread_once_t *once, void (*initialize)(void))
{
    unsigned char *state = (void *)once->__opaque;
    if (*state == 1)
        abort(); /* Recursive initialization cannot complete. */
    if (!*state) {
        *state = 1;
        initialize();
        *state = 2;
    }
    return 0;
}

/* These locks protect private libc state in a process with one thread.
 * Preserve recursion and lifecycle checks without exporting pthread stubs. */
int commonplace_libc_mutex_lock(pthread_mutex_t *mutex)
{
    unsigned *depth = (void *)mutex->__opaque;
    if (*depth == (unsigned)-1)
        return EINVAL;
    ++*depth;
    return 0;
}
int commonplace_libc_mutex_trylock(pthread_mutex_t *mutex)
{
    return commonplace_libc_mutex_lock(mutex);
}
int commonplace_libc_mutex_unlock(pthread_mutex_t *mutex)
{
    unsigned *depth = (void *)mutex->__opaque;
    if (!*depth || *depth == (unsigned)-1)
        return EPERM;
    --*depth;
    return 0;
}
int commonplace_libc_mutex_init(pthread_mutex_t *mutex, const pthread_mutexattr_t *attributes)
{
    if (attributes)
        return ENOTSUP;
    memset(mutex, 0, sizeof(*mutex));
    return 0;
}
int commonplace_libc_mutex_destroy(pthread_mutex_t *mutex)
{
    unsigned *depth = (void *)mutex->__opaque;
    if (*depth)
        return EBUSY;
    *depth = (unsigned)-1;
    return 0;
}
void *commonplace_libc_getspecific(pthread_key_t key)
{
    return key < 768 ? values[key] : 0;
}
int commonplace_libc_setspecific(pthread_key_t key, const void *value)
{
    if (key >= 768 || !keys[key])
        return EINVAL;
    values[key] = (void *)value;
    return 0;
}
int commonplace_libc_key_init(pthread_key_t key, void (*destructor)(void *))
{
    (void)destructor; /* No thread exit exists in this static profile. */
    if (key >= 768)
        return EINVAL;
    keys[key] = 1;
    return 0;
}
int commonplace_libc_key_create(pthread_key_t *key, void (*destructor)(void *))
{
    for (unsigned i = 256; i < 768; ++i)
        if (!keys[i]) {
            *key = i;
            return commonplace_libc_key_init(i, destructor);
        }
    return EAGAIN;
}
int commonplace_libc_key_delete(pthread_key_t key)
{
    if (key >= 768 || !keys[key])
        return EINVAL;
    keys[key] = 0;
    values[key] = 0;
    return 0;
}

int commonplace_libc_rwlock_rdlock(pthread_rwlock_t *lock)
{
    int *count = (void *)lock->__opaque;
    if (*count < 0)
        return EDEADLK;
    ++*count;
    return 0;
}
int commonplace_libc_rwlock_wrlock(pthread_rwlock_t *lock)
{
    int *count = (void *)lock->__opaque;
    if (*count)
        return EDEADLK;
    *count = -1;
    return 0;
}
int commonplace_libc_rwlock_unlock(pthread_rwlock_t *lock)
{
    int *count = (void *)lock->__opaque;
    if (!*count)
        return EPERM;
    if (*count < 0)
        *count = 0;
    else
        --*count;
    return 0;
}
int commonplace_libc_rwlock_init(pthread_rwlock_t *lock, const pthread_rwlockattr_t *attributes)
{
    if (attributes)
        return ENOTSUP;
    memset(lock, 0, sizeof(*lock));
    return 0;
}
int commonplace_libc_rwlock_destroy(pthread_rwlock_t *lock)
{
    return *(int *)(void *)lock->__opaque ? EBUSY : 0;
}
