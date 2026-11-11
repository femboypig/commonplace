#include "runtime.h"
int main(int argc,char **argv)
{
    if (argc!=5 || strcmp(argv[1],"-t") || strcmp(argv[2],"hfs")) {
        print(2,"usage: mount -t hfs device path\n"); return 2;
    }
    long error=mount_hfs(argv[3],argv[4],0);
    if (error<0) { report_error(argv[4],error); return 1; }
    return 0;
}
