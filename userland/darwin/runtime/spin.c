#include <libkern/OSAtomic.h>
void OSSpinLockLock(volatile OSSpinLock *lock)
{
    while (__atomic_exchange_n(lock, 1, __ATOMIC_ACQUIRE))
        __asm__ volatile("pause");
}
void OSSpinLockUnlock(volatile OSSpinLock *lock)
{
    __atomic_store_n(lock, 0, __ATOMIC_RELEASE);
}
bool OSSpinLockTry(volatile OSSpinLock *lock)
{
    return !__atomic_exchange_n(lock, 1, __ATOMIC_ACQUIRE);
}

void spin_lock(volatile OSSpinLock *lock)
{
    OSSpinLockLock(lock);
}
void spin_unlock(volatile OSSpinLock *lock)
{
    OSSpinLockUnlock(lock);
}
