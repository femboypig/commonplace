#include "syscall-numbers.h"
#include "runtime.h"
int main(int argc,char **argv)
{
    unsigned mode=0;
    if (argc<3 || !argv[1][0] || strlen(argv[1])>3) {
        print(2,"usage: chmod octal-mode file ...\n"); return 2;
    }
    for (const char *p=argv[1];*p;++p) {
        if (*p<'0' || *p>'7') { print(2,"chmod: invalid mode\n"); return 2; }
        mode=mode*8+(*p-'0');
    }
    int status=0;
    for (int i=2;i<argc;++i) {
        int fd=(int)sys_open(argv[i],OPEN_READ);
        if (fd<0) { report_error(argv[i],fd); status=1; continue; }
        long error=system_call(SYS_fchmod,fd,mode,0,0,0,0);
        if (error<0) { report_error(argv[i],error); status=1; }
        sys_close(fd);
    }
    return status;
}
