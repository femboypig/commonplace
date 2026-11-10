#include "multiboot.h"

const char *multiboot_read(uint32_t magic, const uint32_t *info, struct multiboot *boot)
{
    if (magic != 0x2badb002 || !info)
        return "expected a multiboot v1 handoff";
    if ((info[0] & 0x48) != 0x48 || info[5] != 1)
        return "pass one kernel module and a firmware memory map";
    const uint32_t *module = (const void *)(uintptr_t)info[6];
    if (!module || module[0] >= module[1])
        return "invalid kernel module";
    boot->kernel = (const void *)(uintptr_t)module[0];
    boot->kernel_size = module[1] - module[0];
    if (!info[12] || info[11] > UINT32_MAX - info[12])
        return "invalid multiboot memory map address";
    return memory_read(&boot->memory, (const void *)(uintptr_t)info[12], info[11]);
}
