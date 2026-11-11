#ifndef COMMONPLACE_STATIC_LIBC_PROFILE_H
#define COMMONPLACE_STATIC_LIBC_PROFILE_H
/* Private support for libc inside single-threaded static bootstrap programs.
 * No pthread API is exported by this profile. */
#include <pthread.h>
#define pthread_once commonplace_libc_once
#define pthread_mutex_lock commonplace_libc_mutex_lock
#define pthread_mutex_unlock commonplace_libc_mutex_unlock
#define pthread_mutex_trylock commonplace_libc_mutex_trylock
#define pthread_mutex_init commonplace_libc_mutex_init
#define pthread_mutex_destroy commonplace_libc_mutex_destroy
#define pthread_getspecific commonplace_libc_getspecific
#define pthread_setspecific commonplace_libc_setspecific
#define pthread_key_init_np commonplace_libc_key_init
#define pthread_key_create commonplace_libc_key_create
#define pthread_key_delete commonplace_libc_key_delete
int commonplace_libc_once(pthread_once_t *, void (*)(void));
int commonplace_libc_mutex_lock(pthread_mutex_t *);
int commonplace_libc_mutex_unlock(pthread_mutex_t *);
int commonplace_libc_mutex_trylock(pthread_mutex_t *);
int commonplace_libc_mutex_init(pthread_mutex_t *, const pthread_mutexattr_t *);
int commonplace_libc_mutex_destroy(pthread_mutex_t *);
void *commonplace_libc_getspecific(pthread_key_t);
int commonplace_libc_setspecific(pthread_key_t, const void *);
int commonplace_libc_key_init(pthread_key_t, void (*)(void *));
int commonplace_libc_key_create(pthread_key_t *, void (*)(void *));
int commonplace_libc_key_delete(pthread_key_t);
#define pthread_rwlock_rdlock commonplace_libc_rwlock_rdlock
#define pthread_rwlock_wrlock commonplace_libc_rwlock_wrlock
#define pthread_rwlock_unlock commonplace_libc_rwlock_unlock
#define pthread_rwlock_init commonplace_libc_rwlock_init
#define pthread_rwlock_destroy commonplace_libc_rwlock_destroy
int commonplace_libc_rwlock_rdlock(pthread_rwlock_t *);
int commonplace_libc_rwlock_wrlock(pthread_rwlock_t *);
int commonplace_libc_rwlock_unlock(pthread_rwlock_t *);
int commonplace_libc_rwlock_init(pthread_rwlock_t *, const pthread_rwlockattr_t *);
int commonplace_libc_rwlock_destroy(pthread_rwlock_t *);
#endif
