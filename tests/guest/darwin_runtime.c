#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <malloc/malloc.h>
#include <pthread.h>
#include <pwd.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define THREADS 12
#define ROUNDS 3000
#define CHECK(condition)                                                                           \
    do                                                                                             \
    {                                                                                              \
        if (!(condition))                                                                          \
        {                                                                                          \
            fprintf(stderr, "runtime check failed: %s:%d: %s (errno=%d)\n", __FILE__, __LINE__,    \
                    #condition, errno);                                                            \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)

static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t ready = PTHREAD_COND_INITIALIZER;
static pthread_rwlock_t rwlock = PTHREAD_RWLOCK_INITIALIZER;
static pthread_once_t once = PTHREAD_ONCE_INIT;
static pthread_key_t key;
static unsigned started, released, counter, once_calls, destroyed;
static int (*plugin_step)(void);
static void (*plugin_register_destructors)(void);

static void initialize_once(void)
{
    usleep(20000);
    ++once_calls;
}

static void destroy_value(void *value)
{
    CHECK((uintptr_t)value >= 1 && (uintptr_t)value <= THREADS);
    __sync_fetch_and_add(&destroyed, 1);
}

static void *allocator_worker(void *argument)
{
    uintptr_t number = (uintptr_t)argument;
    CHECK(pthread_setspecific(key, argument) == 0);
    CHECK(pthread_mutex_lock(&mutex) == 0);
    ++started;
    CHECK(pthread_cond_broadcast(&ready) == 0);
    while (!released)
        CHECK(pthread_cond_wait(&ready, &mutex) == 0);
    CHECK(pthread_mutex_unlock(&mutex) == 0);
    CHECK(pthread_once(&once, initialize_once) == 0);
    void *handle = dlopen("/usr/lib/runtime-plugin.dylib", RTLD_NOW | RTLD_LOCAL);
    CHECK(handle != NULL);
    CHECK(dlsym(handle, "runtime_plugin_step") == (void *)plugin_step);
    CHECK(dlclose(handle) == 0);
    CHECK(plugin_step() == 12);
    CHECK(plugin_step() == 13);
    plugin_register_destructors();
    struct passwd *user = getpwnam("root");
    struct group *group = getgrnam("wheel");
    CHECK(user != NULL && user->pw_uid == 0);
    CHECK(group != NULL && group->gr_gid == 0);
    for (unsigned round = 0; round < ROUNDS; ++round)
    {
        size_t size = 1 + ((round * 7919 + number * 3571) % 70000);
        unsigned char *block = malloc(size);
        CHECK(block != NULL && ((uintptr_t)block & 15) == 0);
        memset(block, (unsigned char)number, size);
        block = realloc(block, size + 137);
        CHECK(block != NULL);
        CHECK(block[0] == number && block[size - 1] == number);
        free(block);
        CHECK(strcmp(user->pw_name, "root") == 0);
        CHECK(strcmp(group->gr_name, "wheel") == 0);
        errno = (int)(100 + number);
        CHECK(pthread_rwlock_rdlock(&rwlock) == 0);
        CHECK(pthread_getspecific(key) == argument);
        CHECK(errno == (int)(100 + number));
        CHECK(pthread_rwlock_unlock(&rwlock) == 0);
        CHECK(pthread_mutex_lock(&mutex) == 0);
        ++counter;
        CHECK(pthread_mutex_unlock(&mutex) == 0);
    }
    return argument;
}

static int pipe_fds[2];
static unsigned cancel_ready, cleanup_calls;
static void cleanup(void *unused)
{
    (void)unused;
    ++cleanup_calls;
}
static void *cancel_worker(void *unused)
{
    (void)unused;
    pthread_cleanup_push(cleanup, NULL);
    __sync_lock_test_and_set(&cancel_ready, 1);
    char byte;
    (void)read(pipe_fds[0], &byte, 1);
    pthread_cleanup_pop(0);
    return NULL;
}

static pthread_once_t canceled_once = PTHREAD_ONCE_INIT;
static unsigned initializer_calls;
static void cancel_initializer(void)
{
    if (__sync_fetch_and_add(&initializer_calls, 1) == 0)
    {
        __sync_lock_test_and_set(&cancel_ready, 1);
        char byte;
        (void)read(pipe_fds[0], &byte, 1);
    }
}
static void *once_worker(void *unused)
{
    (void)unused;
    CHECK(pthread_once(&canceled_once, cancel_initializer) == 0);
    return (void *)23;
}

static void check_cancellation(void *(*routine)(void *))
{
    cancel_ready = 0;
    pthread_t thread;
    CHECK(pthread_create(&thread, NULL, routine, NULL) == 0);
    while (!__sync_fetch_and_add(&cancel_ready, 0))
        usleep(1000);
    usleep(10000);
    CHECK(pthread_cancel(thread) == 0);
    void *result;
    CHECK(pthread_join(thread, &result) == 0);
    CHECK(result == PTHREAD_CANCELED);
}

static unsigned fork_state;
static void fork_prepare(void) { fork_state = 1; }
static void fork_parent(void) { fork_state = 2; }
static void fork_child(void) { fork_state = 3; }

int main(void)
{
    CHECK(dlopen("/bin/no-such-library.dylib", RTLD_NOW) == NULL);
    CHECK(dlerror() != NULL);
    void *plugin = dlopen("/usr/lib/runtime-plugin.dylib", RTLD_NOW | RTLD_LOCAL);
    CHECK(plugin != NULL);
    plugin_step = (int (*)(void))dlsym(plugin, "runtime_plugin_step");
    CHECK(plugin_step != NULL && dlerror() == NULL);
    CHECK(dlsym(plugin, "runtime_plugin_missing_symbol") == NULL);
    CHECK(dlerror() != NULL && dlerror() == NULL);
    plugin_register_destructors =
        (void (*)(void))dlsym(plugin, "runtime_plugin_register_destructors");
    unsigned (*plugin_destroyed)(void) =
        (unsigned (*)(void))dlsym(plugin, "runtime_plugin_destroyed");
    CHECK(plugin_register_destructors != NULL && plugin_destroyed != NULL);
    CHECK(plugin_step() == 12);
    puts("darwin runtime: dynamic loading, constructors and main TLS passed");

    CHECK(pthread_key_create(&key, destroy_value) == 0);
    pthread_t threads[THREADS];
    for (uintptr_t i = 0; i < THREADS; ++i)
        CHECK(pthread_create(&threads[i], NULL, allocator_worker, (void *)(i + 1)) == 0);
    CHECK(pthread_mutex_lock(&mutex) == 0);
    while (started != THREADS)
        CHECK(pthread_cond_wait(&ready, &mutex) == 0);
    released = 1;
    CHECK(pthread_cond_broadcast(&ready) == 0);
    CHECK(pthread_mutex_unlock(&mutex) == 0);

    unsigned progress;
    do
    {
        CHECK(pthread_mutex_lock(&mutex) == 0);
        progress = counter;
        CHECK(pthread_mutex_unlock(&mutex) == 0);
        if (progress < 64)
            usleep(1000);
    } while (progress < 64);
    CHECK(pthread_atfork(fork_prepare, fork_parent, fork_child) == 0);
    for (unsigned attempt = 0; attempt < 4; ++attempt)
    {
        pid_t child = fork();
        CHECK(child >= 0);
        if (!child)
        {
            unsigned char *memory = malloc(16384);
            if (!memory)
                _exit(2);
            memset(memory, 42, 16384);
            free(memory);
            _exit(fork_state == 3 ? 0 : 1);
        }
        int status;
        CHECK(waitpid(child, &status, 0) == child);
        CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 0 && fork_state == 2);
    }
    for (uintptr_t i = 0; i < THREADS; ++i)
    {
        void *result;
        CHECK(pthread_join(threads[i], &result) == 0);
        CHECK(result == (void *)(i + 1));
    }
    CHECK(once_calls == 1 && counter == THREADS * ROUNDS && destroyed == THREADS);
    CHECK(plugin_step() == 13);
    CHECK(plugin_destroyed() == THREADS * 64);
    CHECK(pthread_key_delete(key) == 0);
    puts("darwin runtime: parallel allocation, locks, once, errno, TLS and fork "
         "passed");

    size_t large_size = 192UL * 1024 * 1024;
    unsigned char *large = malloc(large_size);
    CHECK(large != NULL && malloc_size(large) >= large_size);
    for (size_t offset = 0; offset < large_size; offset += 4096)
        large[offset] = 73;
    for (size_t offset = 0; offset < large_size; offset += 4096)
        CHECK(large[offset] == 73);
    free(large);
    for (size_t alignment = 16; alignment <= 65536; alignment <<= 1)
    {
        void *aligned;
        CHECK(posix_memalign(&aligned, alignment, 9001) == 0);
        CHECK(((uintptr_t)aligned & (alignment - 1)) == 0);
        free(aligned);
    }
    puts("darwin runtime: 192 MiB allocation and aligned allocation passed");

    CHECK(pipe(pipe_fds) == 0);
    check_cancellation(cancel_worker);
    CHECK(cleanup_calls == 1);
    cancel_ready = 0;
    pthread_t initializer, waiters[THREADS];
    CHECK(pthread_create(&initializer, NULL, once_worker, NULL) == 0);
    while (!__sync_fetch_and_add(&cancel_ready, 0))
        usleep(1000);
    for (unsigned i = 0; i < THREADS; ++i)
        CHECK(pthread_create(&waiters[i], NULL, once_worker, NULL) == 0);
    usleep(20000);
    CHECK(pthread_cancel(initializer) == 0);
    void *result;
    CHECK(pthread_join(initializer, &result) == 0 && result == PTHREAD_CANCELED);
    for (unsigned i = 0; i < THREADS; ++i)
    {
        CHECK(pthread_join(waiters[i], &result) == 0 && result == (void *)23);
    }
    CHECK(initializer_calls == 2);
    CHECK(close(pipe_fds[0]) == 0 && close(pipe_fds[1]) == 0);
    CHECK(dlclose(plugin) == 0);
    puts("darwin runtime: syscall cancellation, cleanup and once recovery passed");
    return 0;
}
