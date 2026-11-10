#include <stddef.h>

void *memcpy(void *destination, const void *source, size_t size)
{
    unsigned char *dst = destination;
    const unsigned char *src = source;
    for (size_t i = 0; i < size; ++i)
        dst[i] = src[i];
    return destination;
}

void *memset(void *destination, int value, size_t size)
{
    unsigned char *bytes = destination;
    for (size_t i = 0; i < size; ++i)
        bytes[i] = value;
    return destination;
}
