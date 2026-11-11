#include "runtime.h"
int main(int argc, char **argv)
{
    if (argc == 1) return copy_stream(0,1)<0;
    int status = 0;
    for (int i = 1; i < argc; ++i) {
        int fd = !strcmp(argv[i], "-") ? 0 : (int)sys_open(argv[i], OPEN_READ);
        if (fd < 0) { report_error(argv[i], fd); status = 1; continue; }
        int error=copy_stream(fd,1);
        if (error<0) { report_error(argv[i],error); status=1; }
        if (fd) sys_close(fd);
    }
    return status;
}
