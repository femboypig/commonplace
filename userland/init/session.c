#include "syscall-numbers.h"
#include "system.h"
#include "init.h"

int init_console(int controlling)
{
    if (controlling && system_call(SYS_setsid, 0, 0, 0, 0, 0, 0) < 0) return -1;
    int fd = (int)sys_open("/dev/console", OPEN_RDWR | (controlling ? 0 : OPEN_NOCTTY));
    if (fd < 0) return fd;
    for (int standard = 0; standard < 3; ++standard)
        if (sys_dup2(fd, standard) < 0) { sys_close(fd); return -1; }
    if (fd > 2) sys_close(fd);
    if (controlling) {
        int group = (int)sys_getpid();
        if (sys_ioctl(0, 0x20007461, 0) < 0 || sys_ioctl(0, 0x80047476, &group) < 0)
            return -1; /* TIOCSCTTY, TIOCSPGRP in XNU sys/ttycom.h. */
    }
    return 0;
}
