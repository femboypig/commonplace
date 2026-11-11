#ifndef COMMONPLACE_SYSTEM_H
#define COMMONPLACE_SYSTEM_H
#include <stddef.h>
#include <stdint.h>

long system_call(unsigned long number, unsigned long a, unsigned long b,
    unsigned long c, unsigned long d, unsigned long e, unsigned long f);
long sys_read(int fd, void *buffer, size_t size);
long sys_write(int fd, const void *buffer, size_t size);
long sys_open(const char *path, int flags);
long sys_open_mode(const char *, int, unsigned);
long sys_close(int fd);
long sys_getpid(void);
void sys_sleep(unsigned seconds);
void sys_delay(unsigned milliseconds);
void print(int fd, const char *text);
void print_number(int fd, unsigned long value);
int read_line(int fd, char *buffer, size_t capacity);
long sys_fork(void);
struct system_time { int64_t seconds; int32_t microseconds, padding; };
long sys_gettimeofday(struct system_time *);
long sys_pipe(int descriptors[2]);
_Noreturn void sys_exit(int status);
long sys_execve(const char *, char *const *, char *const *);
long sys_wait(int pid, int *status, int options);
long sys_dup2(int, int);
long sys_chdir(const char *);
long sys_fcntl(int, int, void *);
long sys_ioctl(int, unsigned long, void *);
long sys_mkdir(const char *, unsigned);
long sys_unlink(const char *);
long sys_rmdir(const char *);
long sys_getdirentries(int, void *, size_t, int64_t *);
long sys_signal(int, int);
typedef void (*system_signal_handler)(int, void *, void *);
long sys_handle_signal(int, system_signal_handler);
long sys_mount(const char *, const char *, unsigned, const void *);
long sys_sysctl(const int *, unsigned, void *, size_t *, const void *, size_t);
#define OPEN_READ 0
#define OPEN_WRITE 1
#define OPEN_RDWR 2
#define OPEN_APPEND 0x8
#define OPEN_CREATE 0x200
#define OPEN_TRUNCATE 0x400
#define OPEN_EXCLUSIVE 0x800
#define OPEN_NOCTTY 0x20000
#define OPEN_DIRECTORY 0x100000
#define SIGNAL_INT 2
#define SIGNAL_QUIT 3
#define SIGNAL_KILL 9
#define SIGNAL_TSTP 18

#endif
