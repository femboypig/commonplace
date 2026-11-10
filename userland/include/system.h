#ifndef COMMONPLACE_SYSTEM_H
#define COMMONPLACE_SYSTEM_H
#include <stddef.h>
#include <stdint.h>
#include "syscall-numbers.h"

long system_call(unsigned long number, unsigned long a, unsigned long b,
    unsigned long c, unsigned long d, unsigned long e, unsigned long f);
long sys_read(int fd, void *buffer, size_t size);
long sys_write(int fd, const void *buffer, size_t size);
long sys_open(const char *path, int flags);
long sys_close(int fd);
long sys_getpid(void);
void sys_sleep(unsigned seconds);
void print(int fd, const char *text);
void print_number(int fd, unsigned long value);
int read_line(int fd, char *buffer, size_t capacity);
void console_run(int fd);
#endif
