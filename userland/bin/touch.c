#include "syscall-numbers.h"
#include "runtime.h"
int main(int argc,char **argv)
{
    if (argc<2) { print(2,"usage: touch file ...\n"); return 2; }
    int status=0;
    for (int i=1;i<argc;++i) {
        int fd=(int)sys_open(argv[i],OPEN_WRITE|OPEN_CREATE);
        if (fd<0) { report_error(argv[i],fd); status=1; continue; }
        sys_close(fd);
        long error=system_call(SYS_utimes,(uintptr_t)argv[i],0,0,0,0,0);
        if (error<0) { report_error(argv[i],error); status=1; }
    }
    return status;
}
