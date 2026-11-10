#ifndef COMMONPLACE_IMAGE_H
#define COMMONPLACE_IMAGE_H

#include <stddef.h>
#include <stdint.h>

#define IMAGE_SEGMENTS 32

struct image_segment {
    uint32_t address, size, offset, file_size;
};

struct image {
    struct image_segment segments[IMAGE_SEGMENTS];
    uint32_t count, entry, base, end;
};

/* Produce a load plan without writing to any physical destination. */
const char *image_parse(const void *data, size_t size, struct image *image);

#endif
