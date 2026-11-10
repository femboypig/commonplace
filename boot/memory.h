#ifndef COMMONPLACE_MEMORY_H
#define COMMONPLACE_MEMORY_H

#include <stddef.h>
#include <stdint.h>
#include <pexpert/i386/boot.h>

struct memory_region {
    uint64_t start, end;
    uint32_t type;
};

struct memory_reservation {
    uint64_t start, end;
};

#define MEMORY_REGIONS 128

struct memory {
    struct memory_region regions[MEMORY_REGIONS];
    size_t count;
    uint64_t ram_size;
};

const char *memory_read(struct memory *memory, const void *records, size_t size);
int memory_contains(const struct memory *memory, uint64_t start, uint64_t end);
size_t memory_efi(const struct memory *memory,
    const struct memory_reservation *reserved, size_t reservations,
    EfiMemoryRange *output, size_t capacity);

#endif
