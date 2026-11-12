/* Darwin 15 has Mach semaphores but predates ulock. Keep the os_once ABI
 * while parking contending threads in the kernel. Each waiter owns its
 * semaphore and stack record until the initializer has signalled it. */
#include <os/once_private.h>
#include <os/semaphore_private.h>
#include <stdatomic.h>
#include <stdint.h>

struct once_waiter
{
    struct once_waiter *next;
    os_semaphore_t semaphore;
};

#define ONCE_DONE ((uintptr_t)-1)

static void wake_waiters(uintptr_t head)
{
    struct once_waiter *waiter = (void *)head;
    while (waiter->next)
    {
        struct once_waiter *next = waiter->next;
        os_semaphore_t semaphore = waiter->semaphore;
        _os_semaphore_signal(semaphore);
        waiter = next;
    }
}

void _os_once(os_once_t *predicate, void *context, os_function_t initialize)
{
    _Atomic(uintptr_t) *state = (_Atomic(uintptr_t) *)predicate;
    struct once_waiter waiter = {0};
    for (;;)
    {
        uintptr_t previous = atomic_load_explicit(state, memory_order_acquire);
        if (previous == ONCE_DONE)
            break;
        if (!previous)
        {
            waiter.next = NULL;
            if (!atomic_compare_exchange_weak_explicit(state, &previous, (uintptr_t)&waiter,
                                                       memory_order_acq_rel, memory_order_acquire))
                continue;
            initialize(context);
            uintptr_t head = atomic_exchange_explicit(state, ONCE_DONE, memory_order_acq_rel);
            wake_waiters(head);
            break;
        }
        if (!waiter.semaphore)
            waiter.semaphore = _os_semaphore_create();
        waiter.next = (void *)previous;
        if (!atomic_compare_exchange_weak_explicit(state, &previous, (uintptr_t)&waiter,
                                                   memory_order_acq_rel, memory_order_acquire))
            continue;
        _os_semaphore_wait(waiter.semaphore);
    }
    if (waiter.semaphore)
        _os_semaphore_dispose(waiter.semaphore);
}

void __os_once_reset(os_once_t *predicate)
{
    _Atomic(uintptr_t) *state = (_Atomic(uintptr_t) *)predicate;
    uintptr_t head = atomic_exchange_explicit(state, 0, memory_order_acq_rel);
    if (!head || head == ONCE_DONE)
        __builtin_trap();
    wake_waiters(head);
}
