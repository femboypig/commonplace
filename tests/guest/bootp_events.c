#include <CoreFoundation/CoreFoundation.h>
#include "FDSet.h"
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <net/bpf.h>
#include <net/if.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "bootp event check failed at line %d: %s (errno=%d)\n", \
        __LINE__, #test, errno); \
    exit(1); } } while (0)

static void ready(void *context, void *unused)
{
    (void)unused;
    ++*(unsigned *)context;
}

static void wait_ready(unsigned *count)
{
    for (unsigned attempt = 0; attempt < 50 && !*count; ++attempt)
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.1, true);
    CHECK(*count);
}

static FDCalloutRef watch(int fd, unsigned *count)
{
    FDCalloutRef callout = FDCalloutCreate(fd, ready, count, NULL);
    CHECK(callout && FDCalloutGetFD(callout) == fd);
    return callout;
}

static void check_pipe(void)
{
    int descriptors[2];
    CHECK(pipe(descriptors) == 0);
    unsigned count = 0;
    FDCalloutRef callout = watch(descriptors[0], &count);
    for (char expected = 'p'; expected <= 'q'; ++expected) {
        count = 0;
        CHECK(write(descriptors[1], &expected, 1) == 1);
        wait_ready(&count);
        char received;
        CHECK(read(descriptors[0], &received, 1) == 1 && received == expected);
    }
    FDCalloutRelease(&callout);
    CHECK(!callout);
    CHECK(fcntl(descriptors[0], F_GETFD) == -1 && errno == EBADF);
    CHECK(close(descriptors[1]) == 0);
}

static int open_bpf(void)
{
    for (unsigned unit = 0; unit < 256; ++unit) {
        char path[32];
        snprintf(path, sizeof(path), "/dev/bpf%u", unit);
        int fd = open(path, O_RDWR | O_NONBLOCK);
        if (fd >= 0) return fd;
        if (errno != EBUSY) break;
    }
    CHECK(0 && "no BPF descriptor available");
    return -1;
}

static void check_capture(void)
{
    int control = socket(AF_INET, SOCK_DGRAM, 0);
    CHECK(control >= 0);
    struct ifreq request = {0};
    strcpy(request.ifr_name, "lo0");
    struct sockaddr_in *address = (struct sockaddr_in *)&request.ifr_addr;
    address->sin_len = sizeof(*address);
    address->sin_family = AF_INET;
    address->sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    CHECK(ioctl(control, SIOCSIFADDR, &request) == 0);
    CHECK(ioctl(control, SIOCGIFFLAGS, &request) == 0);
    request.ifr_flags |= IFF_UP;
    CHECK(ioctl(control, SIOCSIFFLAGS, &request) == 0);

    int bpf = open_bpf();
    unsigned immediate = 1;
    CHECK(ioctl(bpf, BIOCIMMEDIATE, &immediate) == 0);
    CHECK(ioctl(bpf, BIOCSETIF, &request) == 0);
    unsigned count = 0;
    FDCalloutRef callout = watch(bpf, &count);
    struct sockaddr_in target = {0};
    target.sin_len = sizeof(target);
    target.sin_family = AF_INET;
    target.sin_port = htons(65000);
    target.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    CHECK(sendto(control, "probe", 5, 0, (struct sockaddr *)&target, sizeof(target)) == 5);
    wait_ready(&count);
    unsigned size = 0;
    CHECK(ioctl(bpf, BIOCGBLEN, &size) == 0 && size);
    char *packet = malloc(size);
    CHECK(packet && read(bpf, packet, size) > 0);
    free(packet);
    FDCalloutRelease(&callout);
    CHECK(!callout);
    CHECK(close(control) == 0);
}

int main(void)
{
    CHECK(!FDCalloutCreate(-1, ready, NULL, NULL));
    for (unsigned cycle = 0; cycle < 32; ++cycle) check_pipe();
    check_capture();
    puts("native bootp descriptor readiness and BPF capture passed");
    return 0;
}
