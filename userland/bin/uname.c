#include "runtime.h"
int main(int argc, char **argv)
{
    if (argc > 2 || (argc == 2 && strcmp(argv[1], "-a"))) { print(2, "usage: uname [-a]\n"); return 2; }
    const int keys[] = {1,10,2}; /* KERN_OSTYPE, KERN_HOSTNAME, KERN_OSRELEASE. */
    for (unsigned i=0; i<(argc==2 ? 3u : 1u); ++i) {
        int name[] = {1,keys[i]}; char value[256]; size_t size = sizeof(value);
        long error = sys_sysctl(name, 2, value, &size, 0, 0);
        if (error < 0 || !size || size > sizeof(value)) { report_error("uname", error); return 1; }
        value[sizeof(value)-1]=0;
        if (i) print(1, " "); print(1, value);
    }
    if (argc==2) print(1, " x86_64");
    print(1, "\n"); return 0;
}
