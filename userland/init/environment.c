#include "init.h"

char *const *init_environment(void)
{
    static char *variables[]={
        "PATH=/bin:/usr/bin:/sbin:/usr/sbin", "HOME=/root", "SHELL=/bin/sh",
        "USER=root", "LOGNAME=root", "TERM=vt100", "LANG=C", "TZ=UTC0",
        "PS1=\\h:\\w \\u\\$ ", 0
    };
    return variables;
}
