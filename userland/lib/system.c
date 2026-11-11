#include "syscall-numbers.h"
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
    return system_call(SYS_open, (uintptr_t)path, flags, 0644, 0, 0, 0);
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

_Noreturn void sys_exit(int status)
{
    system_call(SYS_exit, status, 0, 0, 0, 0, 0);
    __builtin_trap();
}
long sys_execve(const char *path, char *const *argv, char *const *env)
{ return system_call(SYS_execve, (uintptr_t)path, (uintptr_t)argv, (uintptr_t)env, 0, 0, 0); }
long sys_wait(int pid, int *status, int options)
{ return system_call(SYS_wait4, pid, (uintptr_t)status, options, 0, 0, 0); }
long sys_dup2(int from, int to)
{ return system_call(SYS_dup2, from, to, 0, 0, 0, 0); }
long sys_chdir(const char *path)
{ return system_call(SYS_chdir, (uintptr_t)path, 0, 0, 0, 0, 0); }
long sys_fcntl(int fd, int command, void *value)
{ return system_call(SYS_fcntl, fd, command, (uintptr_t)value, 0, 0, 0); }
long sys_ioctl(int fd, unsigned long command, void *value)
{ return system_call(SYS_ioctl, fd, command, (uintptr_t)value, 0, 0, 0); }
long sys_mkdir(const char *path, unsigned mode)
{ return system_call(SYS_mkdir, (uintptr_t)path, mode, 0, 0, 0, 0); }
long sys_unlink(const char *path)
{ return system_call(SYS_unlink, (uintptr_t)path, 0, 0, 0, 0, 0); }
long sys_rmdir(const char *path)
{ return system_call(SYS_rmdir, (uintptr_t)path, 0, 0, 0, 0, 0); }
long sys_getdirentries(int fd, void *buffer, size_t size, int64_t *position)
{ return system_call(SYS_getdirentries64, fd, (uintptr_t)buffer, size, (uintptr_t)position, 0, 0); }
long sys_signal(int number, int ignore)
{
    struct { uintptr_t handler, trampoline; uint32_t mask; int flags; } action = {
        ignore ? 1 : 0, 0, 0, 0};
    return system_call(SYS_sigaction, number, (uintptr_t)&action, 0, 0, 0, 0);
}
long sys_mount(const char *type, const char *path, unsigned flags, const void *args)
{ return system_call(SYS_mount, (uintptr_t)type, (uintptr_t)path, flags, (uintptr_t)args, 0, 0); }
long sys_sysctl(const int *name, unsigned count, void *out, size_t *size, const void *in, size_t length)
{ return system_call(SYS_sysctl, (uintptr_t)name, count, (uintptr_t)out, (uintptr_t)size, (uintptr_t)in, length); }

extern void system_signal_trampoline(void);
long sys_handle_signal(int number, system_signal_handler handler)
{
    struct { uintptr_t handler, trampoline; uint32_t mask; int flags; } action={
        (uintptr_t)handler,(uintptr_t)system_signal_trampoline,0,0x40}; /* SA_SIGINFO */
    return system_call(SYS_sigaction,number,(uintptr_t)&action,0,0,0,0);
}
