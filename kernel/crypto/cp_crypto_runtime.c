#include "provider.h"
#include "runtime.h"
#include <stdint.h>
#include <string.h>

#ifdef COMMONPLACE_CRYPTO_HOST
#include <stdio.h>
#include <stdlib.h>
#else
#include <IOKit/IOLib.h>
#include <kern/debug.h>
#endif

struct allocation_header {
    size_t size;
} __attribute__((aligned(16)));

void OPENSSL_die(const char *reason, const char *file, int line)
{
#ifdef COMMONPLACE_CRYPTO_HOST
    fprintf(stderr, "commonplace crypto: %s (%s:%d)\n", reason, file, line);
    abort();
#else
    panic("commonplace crypto: %s (%s:%d)", reason, file, line);
#endif
}

void cp_crypto_fail(const char *reason)
{
    OPENSSL_die(reason, "commonplace crypto", 0);
}

void OPENSSL_cleanse(void *buffer, size_t size)
{
    volatile unsigned char *bytes = buffer;
    while (size--)
        *bytes++ = 0;
}

int CRYPTO_memcmp(const void *first, const void *second, size_t size)
{
    const volatile unsigned char *a = first, *b = second;
    unsigned char difference = 0;
    for (size_t i = 0; i < size; ++i)
        difference |= a[i] ^ b[i];
    return difference;
}

size_t OPENSSL_strlcpy(char *destination, const char *source, size_t capacity)
{
    size_t size = strlen(source);
    if (capacity) {
        size_t copy = size < capacity - 1 ? size : capacity - 1;
        memcpy(destination, source, copy);
        destination[copy] = 0;
    }
    return size;
}

void *CRYPTO_malloc(size_t size, const char *file __attribute__((unused)),
    int line __attribute__((unused)))
{
    if (!size || size > SIZE_MAX - sizeof(struct allocation_header))
        return NULL;
    size_t total = sizeof(struct allocation_header) + size;
#ifdef COMMONPLACE_CRYPTO_HOST
    struct allocation_header *header = malloc(total);
#else
    struct allocation_header *header = IOMalloc(total);
#endif
    if (!header)
        return NULL;
    header->size = total;
    return header + 1;
}

static void crypto_free(void *pointer)
{
    struct allocation_header *header = (struct allocation_header *)pointer - 1;
#ifdef COMMONPLACE_CRYPTO_HOST
    free(header);
#else
    IOFree(header, header->size);
#endif
}

void CRYPTO_free(void *pointer, const char *file __attribute__((unused)),
    int line __attribute__((unused)))
{
    if (pointer)
        crypto_free(pointer);
}

void CRYPTO_clear_free(void *pointer, size_t size,
    const char *file __attribute__((unused)), int line __attribute__((unused)))
{
    if (!pointer)
        return;
    struct allocation_header *header = (struct allocation_header *)pointer - 1;
    if (header->size < sizeof(*header) || size > header->size - sizeof(*header))
        cp_crypto_fail("clear-free exceeds allocation");
    OPENSSL_cleanse(pointer, size);
    crypto_free(pointer);
}
