#define _GNU_SOURCE
#include "arguments.h"
#include "platform.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

int random_bytes(void *out, size_t size) { memset(out, 0x5a, size); return 1; }
uint64_t read_tsc(void) { return 123; }
uint64_t bus_frequency(void) { return 100000000; }
uint32_t find_acpi(void) { return 0xe0000; }
_Noreturn void stop(const char *reason) { fprintf(stderr, "%s\n", reason); abort(); }

static uint32_t word(const unsigned char *bytes)
{
    return bytes[0] | (uint32_t)bytes[1] << 8 | (uint32_t)bytes[2] << 16 | (uint32_t)bytes[3] << 24;
}

static const unsigned char *inspect(const unsigned char *cursor, const unsigned char *end,
    uint32_t root, uint32_t size, unsigned *found)
{
    assert(end - cursor >= 8);
    uint32_t properties = word(cursor), children = word(cursor + 4);
    cursor += 8;
    for (uint32_t i = 0; i < properties; ++i) {
        assert(end - cursor >= 36);
        uint32_t length = word(cursor + 32);
        assert(length <= (size_t)(end - cursor - 36));
        if (!strcmp((const char *)cursor, "RAMDisk")) {
            uint64_t values[2];
            assert(length == sizeof(values));
            memcpy(values, cursor + 36, sizeof(values));
            assert(values[0] == root && values[1] == size);
            ++*found;
        }
        cursor += 36 + ((length + 3) & ~3u);
        assert(cursor <= end);
    }
    for (uint32_t i = 0; i < children; ++i)
        cursor = inspect(cursor, end, root, size, found);
    return cursor;
}

int main(void)
{
    void *buffer = mmap(NULL, BOOT_ARENA_SIZE, PROT_READ | PROT_WRITE,
        MAP_PRIVATE | MAP_ANONYMOUS | MAP_32BIT, -1, 0);
    assert(buffer != MAP_FAILED && (uintptr_t)buffer <= UINT32_MAX - BOOT_ARENA_SIZE);
    uint32_t arena = (uintptr_t)buffer;
    struct image image = {.base = arena - 0x100000, .end = arena};
    struct memory memory = {.regions = {{0, 0x80000000, 1}}, .count = 1, .ram_size = 0x80000000};
    struct memory_reservation loader = {0x70000000, 0x70010000, kEfiReservedMemoryType};
    for (unsigned with_root = 0; with_root < 2; ++with_root) {
        memset(buffer, 0, BOOT_ARENA_SIZE);
        uint32_t root = with_root ? arena + BOOT_ARENA_SIZE : 0;
        uint32_t size = with_root ? 32 * 1024 * 1024 : 0;
        boot_args *args = arguments_build(arena, &image, &memory, loader, root, size);
        assert(args->kaddr + args->ksize == arena + BOOT_ARENA_SIZE + size);
        assert((strstr(args->CommandLine, "rd=md0") != NULL) == with_root);
        unsigned found = 0;
        const unsigned char *tree = (const void *)(uintptr_t)args->deviceTreeP;
        assert(inspect(tree, tree + args->deviceTreeLength, root, size, &found) ==
            tree + args->deviceTreeLength);
        assert(found == with_root);
        if (with_root) {
            const EfiMemoryRange *map = (const void *)(uintptr_t)args->MemoryMap;
            int protected = 0;
            for (size_t i = 0; i < args->MemoryMapSize / sizeof(*map); ++i)
                if (map[i].PhysicalStart <= root &&
                    map[i].PhysicalStart + map[i].NumberOfPages * 4096 >= (uint64_t)root + size)
                    protected = map[i].Type == kEfiLoaderData;
            assert(protected);
        }
    }
    assert(munmap(buffer, BOOT_ARENA_SIZE) == 0);
    return 0;
}
