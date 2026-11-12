#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CHECK(expression)                                                                          \
    do                                                                                             \
    {                                                                                              \
        if (!(expression))                                                                         \
        {                                                                                          \
            fprintf(stderr, "disk I/O check failed at line %d: %s (errno=%d)\n", __LINE__,         \
                    #expression, errno);                                                           \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)

static const char *volumes[2];
static void *worker(void *argument)
{
    unsigned number = (unsigned)(size_t)argument;
    char path[1024];
    CHECK(snprintf(path, sizeof(path), "%s/io-check-%u", volumes[number % 2], number) > 0);
    int fd = open(path, O_CREAT | O_TRUNC | O_RDWR, 0600);
    CHECK(fd >= 0);
    CHECK(fcntl(fd, F_NOCACHE, 1) == 0);
    unsigned char written[4096], read_back[4096];
    for (unsigned round = 0; round < 128; ++round)
    {
        memset(written, (unsigned char)(number * 31 + round), sizeof(written));
        off_t offset = (round % 16) * sizeof(written);
        CHECK(pwrite(fd, written, sizeof(written), offset) == sizeof(written));
        if (round % 8 == 0)
            CHECK(fsync(fd) == 0);
        CHECK(pread(fd, read_back, sizeof(read_back), offset) == sizeof(read_back));
        CHECK(memcmp(written, read_back, sizeof(written)) == 0);
    }
    CHECK(fsync(fd) == 0);
    CHECK(close(fd) == 0);
    CHECK(unlink(path) == 0);
    return NULL;
}

int main(int argc, char **argv)
{
    CHECK(argc == 3);
    volumes[0] = argv[1];
    volumes[1] = argv[2];
    pthread_t threads[4];
    for (size_t i = 0; i < 4; ++i)
        CHECK(pthread_create(&threads[i], NULL, worker, (void *)i) == 0);
    for (unsigned i = 0; i < 4; ++i)
        CHECK(pthread_join(threads[i], NULL) == 0);
    puts("concurrent uncached disk I/O passed");
    return 0;
}
