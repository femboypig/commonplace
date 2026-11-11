#include "syscall-numbers.h"
#include "runtime.h"
int main(int argc,char **argv)
{
    if (argc!=2) { print(2,"usage: umount path\n"); return 2; }
    long error=system_call(SYS_unmount,(uintptr_t)argv[1],0,0,0,0,0);
    if (error<0) { report_error(argv[1],error); return 1; }
    return 0;
}
