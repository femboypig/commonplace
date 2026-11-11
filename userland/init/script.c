#include "syscall-numbers.h"
#include "runtime.h"
#include "init.h"

void init_script(void)
{
    const char *path="/data/rc";
    int fd=(int)sys_open(path,OPEN_READ);
    if (fd==-2) return;
    if (fd<0) { report_error(path,fd); return; }
    struct system_stat status;
    long error=file_status(fd,&status);
    sys_close(fd);
    if (error<0 || (status.mode&0170000)!=0100000) {
        print(2,"init: /data/rc is not a readable regular file\n"); return;
    }
    print(1,"commonplace init: running /data/rc\n");
    long child=sys_fork();
    if (!child) {
        sys_signal(15,0); sys_signal(SIGNAL_INT,0); sys_signal(SIGNAL_QUIT,0);
        if (system_call(SYS_setsid,0,0,0,0,0,0)<0) sys_exit(126);
        char *arguments[]={"/bin/sh","/data/rc",0};
        char *environment[]={"PATH=/bin","HOME=/","TERM=vt100",0};
        sys_execve(arguments[0],arguments,environment);
        sys_exit(127);
    }
    if (child<0) { report_error("startup fork",child); return; }
    int result=0;
    for (unsigned attempt=0;attempt<300;++attempt) {
        if (init_stopping()) return;
        long reaped=sys_wait((int)child,&result,1); /* WNOHANG */
        if (reaped==child) {
            if (result) print(2,"init: startup script failed; continuing with console\n");
            return;
        }
        if (reaped<0 && reaped!=-4) { report_error("startup wait",reaped); return; }
        sys_delay(100);
    }
    print(2,"init: startup script timed out; continuing with console\n");
    system_call(SYS_kill,(unsigned long)-child,SIGNAL_KILL,1,0,0,0);
    long reaped;
    do { reaped=sys_wait((int)child,&result,0); } while (reaped==-4);
}
