#include <fcntl.h>
#include <mach/mach_time.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/disk.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define CHECK(x)                                                                                   \
    do                                                                                             \
    {                                                                                              \
        if (!(x))                                                                                  \
        {                                                                                          \
            perror(#x);                                                                            \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)
#define CHUNK 65536
#define START 65536
#define LENGTH (4 * 1024 * 1024)

static unsigned char pattern(size_t offset)
{
    return (unsigned char)((offset * 37u) ^ (offset >> 9) ^ 0xa5);
}

static unsigned long long elapsed(uint64_t start)
{
    mach_timebase_info_data_t scale;
    CHECK(mach_timebase_info(&scale) == 0);
    return (mach_absolute_time() - start) * scale.numer / scale.denom / 1000;
}

int main(void)
{
    int fd = open("/dev/rcp0", O_RDWR);
    CHECK(fd >= 0);
    unsigned char *allocation = malloc(CHUNK + 1);
    CHECK(allocation != NULL);
    unsigned char *bytes = allocation + 1; /* Exercise unaligned user buffers. */
    uint64_t started = mach_absolute_time();
    for (size_t offset = 0; offset < LENGTH; offset += CHUNK)
    {
        for (size_t i = 0; i < CHUNK; ++i)
            bytes[i] = pattern(offset + i);
        CHECK(pwrite(fd, bytes, CHUNK, START + offset) == CHUNK);
    }
    CHECK(ioctl(fd, DKIOCSYNCHRONIZECACHE, 0) == 0);
    unsigned long long write_us = elapsed(started);
    CHECK(close(fd) == 0);
    fd = open("/dev/rcp0", O_RDONLY);
    CHECK(fd >= 0);
    started = mach_absolute_time();
    for (size_t offset = 0; offset < LENGTH; offset += CHUNK)
    {
        CHECK(pread(fd, bytes, CHUNK, START + offset) == CHUNK);
        for (size_t i = 0; i < CHUNK; ++i)
            if (bytes[i] != pattern(offset + i))
            {
                fprintf(stderr, "raw mismatch: offset=%zu expected=%02x actual=%02x\n", offset + i,
                        pattern(offset + i), bytes[i]);
                exit(1);
            }
    }
    unsigned long long read_us = elapsed(started);
    for (unsigned side = 0; side < 2; ++side)
    {
        CHECK(pread(fd, bytes, 512, side ? START + LENGTH : START - 512) == 512);
        for (unsigned i = 0; i < 512; ++i)
            CHECK(bytes[i] == 0);
    }
    CHECK(close(fd) == 0);
    free(allocation);
    printf("ata transfer passed: bytes=%u write_us=%llu read_us=%llu\n", LENGTH, write_us, read_us);
    return 0;
}
