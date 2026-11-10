#include "system.h"

void init_main(void)
{
    int fd = (int)sys_open("/dev/console", 2);
    if (fd >= 0) {
        print(fd, "\ncommonplace init: pid ");
        print_number(fd, (unsigned long)sys_getpid());
        print(fd, "\ncommonplace bootstrap console\n");
        console_run(fd);
    }
    /* PID 1 must remain alive even if opening or reading the console fails. */
    for (;;) sys_sleep(60);
}
