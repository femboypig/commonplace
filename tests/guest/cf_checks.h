#ifndef COMMONPLACE_CF_CHECKS_H
#define COMMONPLACE_CF_CHECKS_H

#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <stdlib.h>

#define CHECK(value)                                                                               \
    do                                                                                             \
    {                                                                                              \
        if (!(value))                                                                              \
        {                                                                                          \
            fprintf(stderr, "corefoundation check %s:%d: %s\n", __FILE__, __LINE__, #value);       \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)

void check_cf_values(void);
void check_cf_runloop(void);
void check_cf_files(void);

#endif
