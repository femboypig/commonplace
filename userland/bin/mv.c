#include "syscall-numbers.h"
#include "runtime.h"

static int across_filesystems(char **argv)
{
    long child=sys_fork();
    if (!child) {
        char *arguments[]={"cp",argv[1],argv[2],0};
        char *environment[]={"PATH=/bin",0};
        sys_execve("/bin/cp",arguments,environment);
        sys_exit(127);
    }
    if (child<0) { report_error("mv fork",child); return 1; }
    int status;
    long waited;
    do { waited=sys_wait((int)child,&status,0); } while (waited==-4);
    if (waited<0 || status) return 1;
    int fd=(int)sys_open(argv[2],OPEN_READ);
    if (fd<0) { report_error(argv[2],fd); return 1; }
    long error=system_call(SYS_fsync,fd,0,0,0,0,0);
    sys_close(fd);
    if (!error) error=sys_unlink(argv[1]);
    if (error<0) { report_error("mv",error); return 1; }
    return 0;
}

int main(int argc,char **argv)
{
    if (argc!=3) { print(2,"usage: mv source destination\n"); return 2; }
    long error=system_call(SYS_rename,(uintptr_t)argv[1],(uintptr_t)argv[2],0,0,0,0);
    if (error==-18) return across_filesystems(argv); /* EXDEV */
    if (error<0) { report_error(argv[1],error); return 1; }
    return 0;
}
