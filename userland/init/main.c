#include "system.h"

void init_main(void)
{
    for (;;) {
        int fd = (int)sys_open("/dev/console", 2);
        if (fd < 0) {
            sys_sleep(1);
            continue;
        }
        print(fd, "\ncommonplace init: pid ");
        print_number(fd, (unsigned long)sys_getpid());
        print(fd, "\ncommonplace bootstrap console\n");
        console_run(fd);
        print(fd, "reopening console\n");
        sys_close(fd);
        sys_sleep(1);
    }
}
