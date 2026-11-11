#include "runtime.h"
static int copy(int fd)
{
    char buffer[4096];
    for (;;) {
        long size = sys_read(fd, buffer, sizeof(buffer));
        if (size == -4) continue;
        if (size < 0) { report_error("cat read", size); return 1; }
        if (!size) return 0;
        int error = write_all(1, buffer, (size_t)size);
        if (error < 0) { report_error("cat write", error); return 1; }
    }
}
int main(int argc, char **argv)
{
    if (argc == 1) return copy(0);
    int status = 0;
    for (int i = 1; i < argc; ++i) {
        int fd = !strcmp(argv[i], "-") ? 0 : (int)sys_open(argv[i], OPEN_READ);
        if (fd < 0) { report_error(argv[i], fd); status = 1; continue; }
        if (copy(fd)) status = 1;
        if (fd) sys_close(fd);
    }
    return status;
}
