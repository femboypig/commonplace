#include "runtime.h"

long mount_hfs(const char *device, const char *path, unsigned flags)
{
    /* VFS consumes the first pointer; HFS then receives its fixed 40-byte payload. */
    struct {
        const char *device;
        uint32_t uid, gid;
        uint16_t mask, padding;
        uint32_t encoding;
        int32_t minuteswest, dst, flags, journal_buffer, journal_flags, journal_disable;
    } args={device,UINT32_MAX,UINT32_MAX,0755,0,UINT32_MAX,0,0,0,0,0,0};
    _Static_assert(sizeof(args)==48,"Darwin 64-bit HFS mount argument ABI");
    return sys_mount("hfs",path,flags,&args);
}
