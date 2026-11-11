#include "syscall-numbers.h"
#include "runtime.h"
int main(int argc,char **argv)
{
    if (argc!=3) { print(2,"usage: cp source destination\n"); return 2; }
    int source=(int)sys_open(argv[1],OPEN_READ);
    if (source<0) { report_error(argv[1],source); return 1; }
    struct system_stat from,to;
    long error=file_status(source,&from);
    if (error<0 || (from.mode&0170000)!=0100000) {
        report_error(argv[1],error<0 ? error : -22); sys_close(source); return 1;
    }
    int destination=(int)sys_open(argv[2],OPEN_WRITE);
    if (destination==-2) {
        destination=(int)sys_open_mode(argv[2],OPEN_WRITE|OPEN_CREATE|OPEN_EXCLUSIVE,from.mode&0777);
        if (destination==-17) destination=(int)sys_open(argv[2],OPEN_WRITE);
    }
    if (destination<0) { report_error(argv[2],destination); sys_close(source); return 1; }
    error=file_status(destination,&to);
    if (!error && from.device==to.device && from.inode==to.inode) {
        print(2,"cp: source and destination are the same file\n"); error=-22;
    }
    if (!error && (to.mode&0170000)!=0100000) error=-22;
    if (!error) error=system_call(SYS_ftruncate,destination,0,0,0,0,0);
    if (!error) error=copy_stream(source,destination);
    if (error<0) report_error(argv[2],error);
    sys_close(destination); sys_close(source);
    return error<0;
}
