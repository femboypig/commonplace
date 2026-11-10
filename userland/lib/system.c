#include "system.h"

long sys_read(int fd, void *buffer, size_t size)
{
    return system_call(SYS_read, fd, (uintptr_t)buffer, size, 0, 0, 0);
}
long sys_write(int fd, const void *buffer, size_t size)
{
    return system_call(SYS_write, fd, (uintptr_t)buffer, size, 0, 0, 0);
}
long sys_open(const char *path, int flags)
{
    return system_call(SYS_open, (uintptr_t)path, flags, 0, 0, 0, 0);
}
long sys_close(int fd)
{
    return system_call(SYS_close, fd, 0, 0, 0, 0, 0);
}
long sys_getpid(void)
{
    return system_call(SYS_getpid, 0, 0, 0, 0, 0, 0);
}
void sys_sleep(unsigned seconds)
{
    /* Darwin x86_64 user_timeval: time_t is 64 bit, suseconds_t is 32 bit. */
    struct { int64_t seconds; int32_t microseconds, padding; } timeout = {seconds, 0, 0};
    system_call(SYS_select, 0, 0, 0, 0, (uintptr_t)&timeout, 0);
}
