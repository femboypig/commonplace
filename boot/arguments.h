#ifndef COMMONPLACE_ARGUMENTS_H
#define COMMONPLACE_ARGUMENTS_H

#include "image.h"
#include "memory.h"

#define BOOT_ARENA_SIZE 0x20000

boot_args *arguments_build(uint32_t arena, const struct image *image,
    const struct memory *memory, struct memory_reservation loader,
    uint32_t root, uint32_t root_size);

#endif
