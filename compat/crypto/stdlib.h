#ifndef COMMONPLACE_CRYPTO_STDLIB_H
#define COMMONPLACE_CRYPTO_STDLIB_H
#include <stddef.h>
void *malloc(size_t);
void *calloc(size_t, size_t);
void *realloc(void *, size_t);
void free(void *);
void abort(void) __attribute__((noreturn));
int abs(int);
long labs(long);
#endif
