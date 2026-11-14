#ifndef COMMONPLACE_FOUNDATION_CHECKS_H
#define COMMONPLACE_FOUNDATION_CHECKS_H

#include <stdio.h>
#include <stdlib.h>

#define CHECK(value)                                                                               \
    do                                                                                             \
    {                                                                                              \
        if (!(value))                                                                              \
        {                                                                                          \
            fprintf(stderr, "foundation check %s:%d: %s\n", __FILE__, __LINE__, #value);           \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)

void check_native_math(void);
void check_native_unicode(void);

#endif
