#include "runtime.h"
int main(int argc, char **argv)
{
    if (argc < 2) { print(2, "usage: rmdir path ...\n"); return 2; }
    int status = 0;
    for (int i=1; i<argc; ++i) {
        long error = sys_rmdir(argv[i]);
        if (error < 0) { report_error(argv[i], error); status = 1; }
    }
    return status;
}
