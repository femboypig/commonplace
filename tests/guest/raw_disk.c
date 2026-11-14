#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/disk.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define CHECK(expression)                                                                          \
    do                                                                                             \
    {                                                                                              \
        if (!(expression))                                                                         \
        {                                                                                          \
            fprintf(stderr, "raw disk check failed at line %d: %s (errno=%d)\n", __LINE__,         \
                    #expression, errno);                                                           \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)

int main(void)
{
    int scratch = open("/dev/rcp0", O_RDWR);
    int guard = open("/dev/rcp1", O_RDONLY);
    CHECK(scratch >= 0 && guard >= 0);
    uint32_t block_size;
    uint64_t blocks;
    CHECK(ioctl(scratch, DKIOCGETBLOCKSIZE, &block_size) == 0 && block_size == 512);
    CHECK(ioctl(scratch, DKIOCGETBLOCKCOUNT, &blocks) == 0 && blocks >= 32768);
    unsigned char header[512], after[512], written[65536], read_back[65536];
    CHECK(pread(guard, header, sizeof(header), 1024) == sizeof(header));
    CHECK(header[0] == 'H' && header[1] == '+');
    for (unsigned round = 0; round < 16; ++round)
    {
        memset(written, round * 13, sizeof(written));
        off_t offset = 1024 * 1024 + round * sizeof(written);
        CHECK(pwrite(scratch, written, sizeof(written), offset) == sizeof(written));
        CHECK(pread(scratch, read_back, sizeof(read_back), offset) == sizeof(read_back));
        CHECK(memcmp(written, read_back, sizeof(written)) == 0);
    }
    CHECK(pread(scratch, read_back, 512, 1) == -1 && errno == EINVAL);
    CHECK(pwrite(scratch, written, 1, 0) == -1 && errno == EINVAL);
    CHECK(pwrite(scratch, written, 512, blocks * block_size) == -1 && errno == EINVAL);
    CHECK(ioctl(scratch, DKIOCSYNCHRONIZECACHE) == 0);
    CHECK(pread(guard, after, sizeof(after), 1024) == sizeof(after));
    CHECK(memcmp(header, after, sizeof(header)) == 0);
    CHECK(close(scratch) == 0 && close(guard) == 0);
    puts("raw disk: transfer, alignment, bounds and device isolation passed");
    return 0;
}
