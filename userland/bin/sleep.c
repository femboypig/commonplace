#include "runtime.h"
int main(int argc, char **argv)
{
    long seconds = argc == 2 ? parse_unsigned(argv[1]) : -1;
    if (seconds < 0) { print(2, "usage: sleep seconds\n"); return 2; }
    sys_sleep((unsigned)seconds); return 0;
}
