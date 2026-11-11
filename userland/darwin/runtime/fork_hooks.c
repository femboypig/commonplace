#include "libc_private.h"
#include <mach/mach.h>
#include <mach/mach_traps.h>

extern void _libc_fork_init(const struct _libc_functions *);

/* This profile has one thread and no atfork consumers outside libc. */
static void unchanged(void)
{
}
static void child(void)
{
    mach_task_self_ = task_self_trap();
}

void commonplace_init_fork(void)
{
    static const struct _libc_functions functions = {.version = 1,
                                                     .atfork_prepare = unchanged,
                                                     .atfork_parent = unchanged,
                                                     .atfork_child = child};
    _libc_fork_init(&functions);
}
