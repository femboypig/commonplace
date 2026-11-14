#include "dispatch_checks.h"
#include <Block.h>
#include <stdatomic.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;
#include <stdint.h>

static dispatch_once_t once;
static _Atomic unsigned once_calls;

static void queues(void)
{
    dispatch_queue_t serial = dispatch_queue_create("commonplace.serial", NULL);
    dispatch_group_t group = dispatch_group_create();
    dispatch_semaphore_t completed = dispatch_semaphore_create(0);
    CHECK(serial && group && completed);
    __block unsigned count = 0;
    static char key;
    dispatch_queue_set_specific(serial, &key, &key, NULL);
    for (unsigned i = 0; i < 100; ++i)
        dispatch_group_async(group, serial, ^{
          CHECK(count++ == i);
          CHECK(dispatch_get_specific(&key) == &key);
        });
    dispatch_group_notify(group, serial, ^{
      dispatch_semaphore_signal(completed);
    });
    WAIT(completed);
    CHECK(count == 100);

    dispatch_queue_t concurrent =
        dispatch_queue_create("commonplace.concurrent", DISPATCH_QUEUE_CONCURRENT);
    CHECK(concurrent);
    __block _Atomic unsigned total = 0;
    for (unsigned i = 0; i < 100; ++i)
        dispatch_async(concurrent, ^{
          dispatch_once(&once, ^{
            atomic_fetch_add(&once_calls, 1);
          });
          atomic_fetch_add(&total, i + 1);
        });
    dispatch_barrier_sync(concurrent, ^{
      CHECK(atomic_load(&total) == 5050 && atomic_load(&once_calls) == 1);
    });
    atomic_store(&total, 0);
    dispatch_apply(100, concurrent, ^(size_t i) {
      atomic_fetch_add(&total, i + 1);
    });
    CHECK(atomic_load(&total) == 5050);

    dispatch_suspend(serial);
    __block int ran = 0;
    dispatch_block_t block = dispatch_block_create(0, ^{
      ran = 1;
    });
    CHECK(block);
    dispatch_block_cancel(block);
    dispatch_async(serial, block);
    dispatch_resume(serial);
    CHECK(dispatch_block_wait(block, dispatch_time(DISPATCH_TIME_NOW, 5 * NSEC_PER_SEC)) == 0);
    CHECK(!ran && dispatch_block_testcancel(block));
    Block_release(block);
    CHECK(dispatch_semaphore_wait(completed, dispatch_time(DISPATCH_TIME_NOW, NSEC_PER_MSEC)) != 0);
    dispatch_release(concurrent);
    dispatch_release(completed);
    dispatch_release(group);
    dispatch_release(serial);
    puts("dispatch queues, groups, barriers, once and blocks passed");
    fflush(stdout);
}

int main(void)
{
    queues();
    volatile unsigned __int128 dividend = ((unsigned __int128)1 << 127) - 1;
    volatile unsigned __int128 divisor = ((unsigned __int128)1 << 64) - 1;
    CHECK(dividend / divisor == ((unsigned __int128)1 << 63));
    CHECK(dividend % divisor == (((unsigned __int128)1 << 63) - 1));
    char *arguments[] = {"/bin/dispatch-main-check", NULL};
    pid_t child = fork();
    CHECK(child >= 0);
    if (!child)
    {
        execve(arguments[0], arguments, environ);
        _exit(127);
    }
    int status;
    CHECK(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 0);
    check_dispatch_sources();
    check_dispatch_io();
    puts("native dispatch checks passed");
    return 0;
}
