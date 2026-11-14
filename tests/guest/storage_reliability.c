#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CHECK(x)                                                                                   \
    do                                                                                             \
    {                                                                                              \
        if (!(x))                                                                                  \
        {                                                                                          \
            fprintf(stderr, "storage check line %d: errno %d\n", __LINE__, errno);                 \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)
static unsigned char block[65536];

static void pattern(unsigned number)
{
    for (unsigned i = 0; i < sizeof(block); ++i)
        block[i] = (unsigned char)(i * 17 + number);
}

static void anchor(const char *path, int writing)
{
    int fd = open(path, writing ? O_CREAT | O_TRUNC | O_WRONLY : O_RDONLY, 0600);
    if (fd < 0)
        perror(path);
    CHECK(fd >= 0);
    for (unsigned n = 0; n < 16; ++n)
    {
        pattern(n);
        if (writing)
            CHECK(write(fd, block, sizeof(block)) == sizeof(block));
        else
        {
            unsigned char actual[sizeof(block)];
            CHECK(read(fd, actual, sizeof(actual)) == sizeof(actual));
            CHECK(memcmp(block, actual, sizeof(block)) == 0);
        }
    }
    if (writing)
    {
        CHECK(fsync(fd) == 0);
        int parent = open(!strncmp(path, "/root/", 6) ? "/root" : "/data", O_RDONLY);
        CHECK(parent >= 0);
        CHECK(fsync(parent) == 0);
        CHECK(close(parent) == 0);
        CHECK(fcntl(fd, F_FULLFSYNC) == 0);
    }
    CHECK(close(fd) == 0);
}

int main(int argc, char **argv)
{
    CHECK(argc == 2);
    if (!strcmp(argv[1], "crash"))
    {
        anchor("/root/durable", 1);
        anchor("/data/durable", 1);
        puts("durable checkpoint");
        fflush(stdout);
        for (unsigned n = 0;; ++n)
        {
            const char *path = n % 2 ? "/root/churn" : "/data/churn";
            int fd = open(path, O_CREAT | O_TRUNC | O_WRONLY, 0600);
            CHECK(fd >= 0);
            pattern(n);
            CHECK(write(fd, block, sizeof(block)) == sizeof(block));
            CHECK(fsync(fd) == 0);
            CHECK(close(fd) == 0);
            CHECK(unlink(path) == 0);
            printf("transaction %u\n", n);
            fflush(stdout);
        }
    }
    if (!strcmp(argv[1], "verify"))
    {
        anchor("/root/durable", 0);
        anchor("/data/durable", 0);
        puts("durable files verified");
        return 0;
    }
    CHECK(!strcmp(argv[1], "fill"));
    anchor("/data/sentinel", 1);
    int fd = open("/data/full", O_CREAT | O_TRUNC | O_WRONLY, 0600);
    CHECK(fd >= 0);
    unsigned count = 0;
    for (;;)
    {
        ssize_t size = write(fd, block, sizeof(block));
        if (size < 0)
        {
            CHECK(errno == ENOSPC);
            break;
        }
        CHECK(size > 0);
        CHECK(++count < 4096);
    }
    CHECK(close(fd) == 0);
    CHECK(unlink("/data/full") == 0);
    anchor("/data/sentinel", 0);
    anchor("/data/after-full", 1);
    anchor("/data/after-full", 0);
    puts("full volume recovery verified");
    return 0;
}
