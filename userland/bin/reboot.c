#include "syscall-numbers.h"
#include "runtime.h"
int main(void)
{
    long error=system_call(SYS_reboot,0,0,0,0,0,0);
    if (error<0) report_error("reboot",error);
    return 1;
}
