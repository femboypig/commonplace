#include "image.h"

static uint32_t read32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
        (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint64_t read64(const unsigned char *p)
{
    return read32(p) | (uint64_t)read32(p + 4) << 32;
}

const char *image_parse(const void *data, size_t size, struct image *image)
{
    const unsigned char *bytes = data;
    uint32_t cursor = 32, limit, commands;
    uint64_t entry = 0;
    *image = (struct image){.base = UINT32_MAX};
    if (size < 32 || read32(bytes) != 0xfeedfacf ||
        read32(bytes + 4) != 0x1000007 || read32(bytes + 12) != 2)
        return "expected an x86_64 Mach-O executable";
    commands = read32(bytes + 16);
    if (read32(bytes + 20) > size - 32)
        return "load commands exceed the image";
    limit = 32 + read32(bytes + 20);
    if (limit < 32)
        return "load command size overflow";
    for (uint32_t i = 0; i < commands; ++i) {
        if (limit - cursor < 8)
            return "missing load command";
        const unsigned char *command = bytes + cursor;
        uint32_t kind = read32(command), length = read32(command + 4);
        if (length < 8 || length % 8 || length > limit - cursor)
            return "invalid load command size";
        if (kind == 0x19) {
            if (length < 72 || (length - 72) / 80 != read32(command + 64) ||
                (length - 72) % 80)
                return "invalid segment command";
            uint64_t address = read64(command + 24), memory = read64(command + 32);
            uint64_t offset = read64(command + 40), file = read64(command + 48);
            if (file > memory || offset > size || file > size - offset)
                return "segment exceeds the image";
            if (memory) {
                if (address >> 32 != 0xffffff80 || (uint32_t)address < 0x100000 ||
                    memory > 0x8000000 || (uint32_t)address > 0x8000000 - memory)
                    return "segment exceeds the bootstrap address window";
                if (image->count == IMAGE_SEGMENTS)
                    return "too many segments";
                struct image_segment segment = {
                    (uint32_t)address, (uint32_t)memory, (uint32_t)offset, (uint32_t)file
                };
                for (uint32_t j = 0; j < image->count; ++j) {
                    const struct image_segment *previous = &image->segments[j];
                    if (segment.address < previous->address + previous->size &&
                        previous->address < segment.address + segment.size)
                        return "overlapping segments";
                }
                image->segments[image->count++] = segment;
                if (segment.address < image->base)
                    image->base = segment.address;
                if (segment.address + segment.size > image->end)
                    image->end = segment.address + segment.size;
            }
        } else if (kind == 5) {
            if (length != 184 || read32(command + 8) != 4 || read32(command + 12) != 42 || entry)
                return "unsupported initial thread state";
            entry = read64(command + 144);
        }
        cursor += length;
    }
    if (cursor != limit || entry >> 32 != 0xffffff80)
        return "missing or invalid kernel entry";
    image->entry = (uint32_t)entry;
    for (uint32_t i = 0; i < image->count; ++i) {
        const struct image_segment *segment = &image->segments[i];
        if (image->entry >= segment->address &&
            image->entry - segment->address < segment->file_size)
            return NULL;
    }
    return "kernel entry is outside loaded data";
}
