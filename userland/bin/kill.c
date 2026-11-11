#include "syscall-numbers.h"
#include "runtime.h"
int main(int argc, char **argv)
{
    int number = 15, first = 1;
    if (argc > 1 && argv[1][0]=='-') {
        long value = parse_unsigned(argv[1]+1);
        if (value < 1 || value > 31) { print(2, "kill: invalid signal\n"); return 2; }
        number = (int)value; first = 2;
    }
    if (argc <= first) { print(2, "usage: kill [-signal] pid ...\n"); return 2; }
    int status = 0;
    for (int i=first; i<argc; ++i) {
        long pid = parse_unsigned(argv[i]);
        if (pid < 2) { print(2, "kill: expected a PID greater than 1\n"); status=1; continue; }
        long error = system_call(SYS_kill, pid, number, 1, 0, 0, 0);
        if (error < 0) { report_error(argv[i], error); status=1; }
    }
    return status;
}
