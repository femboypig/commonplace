#include "multiboot.h"

const char *multiboot_read(uint32_t magic, const uint32_t *info, struct multiboot *boot)
{
    if (magic != 0x2badb002 || !info)
        return "expected a multiboot v1 handoff";
    if ((info[0] & 0x48) != 0x48 || info[5] < 1 || info[5] > 2)
        return "pass a kernel, an optional root image and a firmware memory map";
    const uint32_t *module = (const void *)(uintptr_t)info[6];
    if (!module || info[6] > UINT32_MAX - info[5] * 16)
        return "invalid module table";
    for (uint32_t i = 0; i < info[5]; ++i)
        if (module[i * 4] >= module[i * 4 + 1])
            return "invalid module bounds";
    boot->kernel = (const void *)(uintptr_t)module[0];
    boot->kernel_size = module[1] - module[0];
    boot->root = info[5] == 2 ? (const void *)(uintptr_t)module[4] : 0;
    boot->root_size = info[5] == 2 ? module[5] - module[4] : 0;
    if (boot->root && (module[0] < module[5] && module[4] < module[1]))
        return "overlapping modules";
    if (!info[12] || info[11] > UINT32_MAX - info[12])
        return "invalid multiboot memory map address";
    return memory_read(&boot->memory, (const void *)(uintptr_t)info[12], info[11]);
}
