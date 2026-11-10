#include "arguments.h"
#include "platform.h"
#include "tree.h"

static void copy(void *destination, const void *source, size_t size)
{
    for (size_t i = 0; i < size; ++i)
        ((unsigned char *)destination)[i] = ((const unsigned char *)source)[i];
}

/* BIOS supplies ACPI; these EFI-format records describe it to Darwin. */
static void system_table(uint32_t *table)
{
    table[0] = 0x20494249;
    table[1] = 0x54535953;
    table[2] = 0x20000;
    table[3] = 120;
    uint32_t crc = UINT32_MAX;
    for (size_t i = 0; i < 120; ++i) {
        crc ^= ((unsigned char *)table)[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ (0xedb88320u & -(crc & 1));
    }
    table[4] = ~crc;
}

static size_t device_tree(void *buffer, size_t capacity, const char *command_line,
    uint64_t frequency)
{
    struct tree tree;
    uint8_t seed[64];
    uint64_t initial_tsc = read_tsc();
    uint64_t acpi = find_acpi();
    const uint8_t acpi_guid[16] = {
        0x30, 0x2d, 0x9d, 0xeb, 0x88, 0x2d, 0xd3, 0x11,
        0x9a, 0x16, 0x00, 0x90, 0x27, 0x3f, 0xc1, 0x4d
    };
    if (!random_bytes(seed, sizeof(seed)))
        stop("hardware random seed unavailable");
    if (!acpi)
        stop("ACPI root pointer not found");
    tree_init(&tree, buffer, capacity);
    tree_begin(&tree, "/");
    tree_property(&tree, "compatible", "ACPI", 5);
    tree_property(&tree, "model", "commonplace", 12);
    tree_begin(&tree, "chosen");
    size_t length = 0;
    while (command_line[length])
        ++length;
    tree_property(&tree, "boot-args", command_line, length + 1);
    tree_property(&tree, "random-seed", seed, sizeof(seed));
    tree_begin(&tree, "memory-map");
    tree_end(&tree);
    tree_end(&tree);
    tree_begin(&tree, "efi");
    tree_property(&tree, "firmware-abi", "EFI64", 6);
    tree_begin(&tree, "platform");
    tree_property(&tree, "FSBFrequency", &frequency, sizeof(frequency));
    tree_property(&tree, "InitialTSC", &initial_tsc, sizeof(initial_tsc));
    tree_end(&tree);
    tree_begin(&tree, "configuration-table");
    tree_begin(&tree, "EB9D2D30-2D88-11D3-9A16-0090273FC14D");
    tree_property(&tree, "guid", acpi_guid, sizeof(acpi_guid));
    tree_property(&tree, "table", &acpi, sizeof(acpi));
    tree_end(&tree);
    tree_end(&tree);
    tree_end(&tree);
    tree_end(&tree);
    return tree_size(&tree);
}

boot_args *arguments_build(uint32_t arena, const struct image *image,
    const struct memory *memory, struct memory_reservation loader)
{
    _Static_assert(sizeof(boot_args) == 4096, "Darwin boot argument ABI");
    _Static_assert(sizeof(EfiMemoryRange) == 40, "EFI memory descriptor ABI");
    boot_args *args = (void *)(uintptr_t)arena;
    args->Revision = kBootArgsRevision;
    args->Version = kBootArgsVersion;
    args->efiMode = kBootArgsEfiMode64;
    const char command_line[] = "-v serial=3 debug=0x108 keepsyms=1 cpus=1";
    copy(args->CommandLine, command_line, sizeof(command_line));
    args->kaddr = image->base;
    args->ksize = arena + BOOT_ARENA_SIZE - image->base;
    args->PhysicalMemorySize = memory->ram_size;
    args->FSBFrequency = bus_frequency();
    if (!args->FSBFrequency)
        stop("QEMU timer frequencies unavailable; enable invariant TSC and vmware-cpuid-freq");
    args->Video = (Boot_Video){0xb8000, FB_TEXT_MODE, 160, 80, 25, 0};
    args->MemoryMap = arena + 4096;
    args->MemoryMapDescriptorSize = sizeof(EfiMemoryRange);
    args->MemoryMapDescriptorVersion = 1;
    const struct memory_reservation reserved[] = {
        {0, 0x100000, kEfiReservedMemoryType},
        {image->base, arena + BOOT_ARENA_SIZE, kEfiLoaderData}, loader
    };
    size_t count = memory_efi(memory, reserved, 3,
        (void *)(uintptr_t)args->MemoryMap, 256);
    if (!count)
        stop("EFI memory descriptor capacity exceeded");
    args->MemoryMapSize = count * sizeof(EfiMemoryRange);
    args->efiSystemTable = arena + 0x4000;
    system_table((void *)(uintptr_t)args->efiSystemTable);
    args->deviceTreeP = arena + 0x5000;
    args->deviceTreeLength = device_tree((void *)(uintptr_t)args->deviceTreeP,
        BOOT_ARENA_SIZE - 0x5000, command_line, args->FSBFrequency);
    if (!args->deviceTreeLength)
        stop("device tree capacity exceeded");
    return args;
}
