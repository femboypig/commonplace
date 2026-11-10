#ifndef COMMONPLACE_PROFILE_STRING_H
#define COMMONPLACE_PROFILE_STRING_H
#include <stddef.h>

/* Implementations are supplied by XNU's libkern. */
void *memcpy(void *restrict destination, const void *restrict source, size_t count);
void *memset(void *destination, int value, size_t count);
#endif
