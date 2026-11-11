#include "runtime.h"
#include "init.h"

void init_system(void)
{
    const int hostname[] = {1, 10}; /* CTL_KERN, KERN_HOSTNAME. */
    const char name[] = "commonplace";
    long error = sys_sysctl(hostname, 2, 0, 0, name, sizeof(name) - 1);
    if (error < 0) report_error("hostname", error);
    /* VFC_VFSLOCALARGS consumes the device pointer before passing HFS arguments. */
    struct {
        const char *device;
        uint32_t uid, gid;
        uint16_t mask, padding;
        uint32_t encoding;
        int32_t minuteswest, dst, flags, journal_buffer, journal_flags, journal_disable;
    } args = {0, UINT32_MAX, UINT32_MAX, 0755, 0, UINT32_MAX, 0, 0, 0, 0, 0, 0};
    _Static_assert(sizeof(args) == 48, "Darwin 64-bit HFS mount argument ABI");
    error = sys_mount("hfs", "/", 0x10000, &args); /* MNT_UPDATE: make the RAM root writable. */
    if (error < 0) report_error("root remount", error);
    else print(1, "commonplace init: writable RAM root\n");
}
