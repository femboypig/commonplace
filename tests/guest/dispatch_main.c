#include "dispatch_checks.h"

int main(void)
{
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 10 * NSEC_PER_MSEC), dispatch_get_main_queue(),
                   ^{
                     puts("dispatch main queue after fork/exec passed");
                     exit(0);
                   });
    dispatch_main();
}
