#ifndef COMMONPLACE_RUNTIME_H
#define COMMONPLACE_RUNTIME_H
#include "system.h"
size_t strlen(const char *);
int strcmp(const char *, const char *);
void *memcpy(void *, const void *, size_t);
void *memset(void *, int, size_t);
int path_join(char *, size_t, const char *, const char *);
int get_directory(char *, size_t);
int write_all(int, const void *, size_t);
void report_error(const char *, long);
long parse_unsigned(const char *);
#endif
