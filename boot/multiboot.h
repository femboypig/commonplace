#ifndef COMMONPLACE_MULTIBOOT_H
#define COMMONPLACE_MULTIBOOT_H

#include "memory.h"

struct multiboot {
    const void *kernel;
    uint32_t kernel_size;
    const void *root;
    uint32_t root_size;
    int disk_root;
    struct memory memory;
};

const char *multiboot_read(uint32_t magic, const uint32_t *info, struct multiboot *boot);

#endif
