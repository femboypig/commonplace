#ifndef COMMONPLACE_DISPATCH_CHECKS_H
#define COMMONPLACE_DISPATCH_CHECKS_H

#include <dispatch/dispatch.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

#define CHECK(value)                                                                               \
    do                                                                                             \
    {                                                                                              \
        if (!(value))                                                                              \
        {                                                                                          \
            fprintf(stderr, "dispatch check %s:%d: errno %d\n", __FILE__, __LINE__, errno);        \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)
#define WAIT(semaphore)                                                                            \
    CHECK(dispatch_semaphore_wait((semaphore),                                                     \
                                  dispatch_time(DISPATCH_TIME_NOW, 5 * NSEC_PER_SEC)) == 0)

void check_dispatch_sources(void);
void check_dispatch_io(void);

#endif
