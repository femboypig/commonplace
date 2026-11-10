#include "arguments.h"
#include "multiboot.h"
#include "platform.h"

extern char loader_start[], loader_end[];
extern void *memset(void *, int, size_t);
extern void *memcpy(void *, const void *, size_t);

void loader_main(uint32_t magic, const uint32_t *info)
{
    struct multiboot boot;
    struct image image;
    console_init();
    console_write("commonplace: multiboot loader\n");
    const char *error = multiboot_read(magic, info, &boot);
    if (error)
        stop(error);
    error = image_parse(boot.kernel, boot.kernel_size, &image);
    if (error)
        stop(error);
    uint32_t arena = (image.end + 4095) & ~4095u;
    struct memory_reservation loader = {
        .start = (uintptr_t)loader_start, .end = (uintptr_t)loader_end,
        .type = kEfiReservedMemoryType
    };
    uint32_t module_start = (uintptr_t)boot.kernel;
    uint32_t module_end = module_start + boot.kernel_size;
    if (module_start < loader.start)
        loader.start = module_start & ~4095u;
    if (module_end > loader.end)
        loader.end = ((uint64_t)module_end + 4095) & ~UINT64_C(4095);
    if (!memory_contains(&boot.memory, image.base, arena + BOOT_ARENA_SIZE) ||
        (image.base < loader.end && arena + BOOT_ARENA_SIZE > loader.start))
        stop("kernel destination is not available RAM");
    for (uint32_t i = 0; i < image.count; ++i) {
        const struct image_segment *segment = &image.segments[i];
        void *destination = (void *)(uintptr_t)segment->address;
        memset(destination, 0, segment->size);
        memcpy(destination, (const unsigned char *)boot.kernel + segment->offset,
            segment->file_size);
    }
    memset((void *)(uintptr_t)arena, 0, BOOT_ARENA_SIZE);
    boot_args *args = arguments_build(arena, &image, &boot.memory, loader);
    console_write("kernel entry ");
    console_hex(image.entry);
    console_write(", boot arguments ");
    console_hex((uintptr_t)args);
    console_write("\n");
    mask_legacy_pic();
    enter_kernel(image.entry, (uintptr_t)args);
}
