#include <execinfo.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "backtrace check failed at line %d: %s\n", __LINE__, #test); \
    exit(1); } } while (0)

__attribute__((noinline)) static void capture(void)
{
    void *frames[32];
    int count = backtrace(frames, 32);
    CHECK(count >= 2 && count <= 32);
    char **symbols = backtrace_symbols(frames, count);
    CHECK(symbols);
    int found_image = 0;
    for (int i = 0; i < count; ++i) {
        CHECK(frames[i] && symbols[i] && symbols[i][0]);
        if (strstr(symbols[i], "backtrace")) found_image = 1;
    }
    CHECK(found_image);
    free(symbols);
    int descriptors[2];
    CHECK(pipe(descriptors) == 0);
    backtrace_symbols_fd(frames, count, descriptors[1]);
    CHECK(close(descriptors[1]) == 0);
    char buffer[8192];
    ssize_t size = read(descriptors[0], buffer, sizeof(buffer));
    CHECK(size > 0 && memchr(buffer, '\n', (size_t)size));
    CHECK(close(descriptors[0]) == 0);
}

static void *worker(void *context)
{
    (void)context;
    capture();
    return NULL;
}

int main(void)
{
    capture();
    pthread_t thread;
    CHECK(pthread_create(&thread, NULL, worker, NULL) == 0);
    CHECK(pthread_join(thread, NULL) == 0);
    puts("native backtraces and symbol formatting passed on main and worker stacks");
    return 0;
}
