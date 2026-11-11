#include "syscall-numbers.h"
#include "runtime.h"
int main(void)
{
    long error=system_call(SYS_reboot,8,0,0,0,0,0); /* RB_HALT: sync and unmount first. */
    if (error<0) report_error("poweroff",error);
    return 1;
}
