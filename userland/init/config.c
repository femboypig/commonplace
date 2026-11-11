#include "runtime.h"
#include "init.h"

void init_system(void)
{
    const int hostname[] = {1, 10}; /* CTL_KERN, KERN_HOSTNAME. */
    const char name[] = "commonplace";
    long error = sys_sysctl(hostname, 2, 0, 0, name, sizeof(name) - 1);
    if (error < 0) report_error("hostname", error);
    error = mount_hfs(0,"/",0x10000);
    if (error < 0) report_error("root remount", error);
    else print(1, "commonplace init: writable RAM root\n");
    int disk=(int)sys_open("/dev/cp0",OPEN_RDWR);
    if (disk>=0) {
        sys_close(disk);
        error=mount_hfs("/dev/cp0","/data",0);
        if (error<0) report_error("/data mount",error);
        else print(1,"commonplace init: persistent /data mounted\n");
    }
}
