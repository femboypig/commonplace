#include "memory.h"

static uint32_t read32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
        (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint64_t read64(const unsigned char *p)
{
    return read32(p) | (uint64_t)read32(p + 4) << 32;
}

const char *memory_read(struct memory *memory, const void *records, size_t size)
{
    const unsigned char *p = records;
    *memory = (struct memory){0};
    while (size) {
        if (size < 4 || read32(p) < 20 || read32(p) > size - 4)
            return "invalid multiboot memory record";
        uint64_t start = read64(p + 4), length = read64(p + 12);
        if (!length || length > UINT64_MAX - start || memory->count == MEMORY_REGIONS)
            return "invalid memory range";
        struct memory_region region = {start, start + length, read32(p + 20)};
        size_t index = memory->count;
        while (index && memory->regions[index - 1].start > start) {
            memory->regions[index] = memory->regions[index - 1];
            --index;
        }
        memory->regions[index] = region;
        ++memory->count;
        if (region.type == 1)
            memory->ram_size += length;
        size_t step = (size_t)read32(p) + 4;
        p += step;
        size -= step;
    }
    for (size_t i = 1; i < memory->count; ++i)
        if (memory->regions[i - 1].end > memory->regions[i].start)
            return "overlapping firmware memory ranges";
    return memory->count ? NULL : "missing firmware memory map";
}

int memory_contains(const struct memory *memory, uint64_t start, uint64_t end)
{
    for (size_t i = 0; i < memory->count; ++i) {
        const struct memory_region *region = &memory->regions[i];
        if (region->type == 1 && region->start <= start && region->end >= end && start < end)
            return 1;
    }
    return 0;
}

size_t memory_efi(const struct memory *memory,
    const struct memory_reservation *reserved, size_t reservations,
    EfiMemoryRange *output, size_t capacity)
{
    size_t count = 0;
    for (size_t i = 0; i < reservations; ++i)
        if (reserved[i].start >= reserved[i].end ||
            (reserved[i].start | reserved[i].end) & 4095)
            return 0;
    for (size_t i = 0; i < memory->count; ++i) {
        const struct memory_region *region = &memory->regions[i];
        if (region->start > UINT64_MAX - 4095)
            return 0;
        uint64_t cursor = (region->start + 4095) & ~UINT64_C(4095);
        uint64_t end = region->end & ~UINT64_C(4095);
        while (cursor < end) {
            uint64_t next = end;
            uint32_t type = kEfiReservedMemoryType;
            if (region->type == 1) type = kEfiConventionalMemory;
            if (region->type == 3) type = kEfiACPIReclaimMemory;
            if (region->type == 4) type = kEfiACPIMemoryNVS;
            for (size_t j = 0; j < reservations; ++j) {
                if (cursor >= reserved[j].start && cursor < reserved[j].end)
                    type = reserved[j].type;
                if (reserved[j].start > cursor && reserved[j].start < next)
                    next = reserved[j].start;
                if (reserved[j].end > cursor && reserved[j].end < next)
                    next = reserved[j].end;
            }
            if (count == capacity)
                return 0;
            output[count++] = (EfiMemoryRange){
                .Type = type,
                .PhysicalStart = cursor, .NumberOfPages = (next - cursor) >> 12
            };
            cursor = next;
        }
    }
    return count;
}
