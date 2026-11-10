#include <assert.h>
#include <stdlib.h>
#include <string.h>

extern void commonplace_qsort(void *, size_t, size_t, int (*)(const void *, const void *));
static size_t element_size;

static int compare(const void *left, const void *right)
{
    return memcmp(left, right, element_size);
}

int main(void)
{
    size_t sizes[] = {1, 2, 3, 4, 7, 8, 16, 24};
    size_t counts[] = {0, 1, 2, 6, 7, 16, 127, 257};
    for (size_t s = 0; s < sizeof(sizes) / sizeof(sizes[0]); ++s) {
        element_size = sizes[s];
        for (size_t n = 0; n < sizeof(counts) / sizeof(counts[0]); ++n) {
            size_t bytes = element_size * counts[n];
            for (size_t offset = 0; offset < sizeof(long); ++offset) {
                size_t prefix = 16 + offset;
                unsigned char *actual = malloc(prefix + bytes + 16);
                unsigned char *expected = malloc(bytes + 1);
                assert(actual && expected);
                memset(actual, 0xa5, prefix + bytes + 16);
                for (size_t i = 0; i < counts[n]; ++i)
                    for (size_t j = 0; j < element_size; ++j)
                        actual[prefix + i * element_size + j] = (i * 13 + i / 3 + j) % 11;
                memcpy(expected, actual + prefix, bytes);
                qsort(expected, counts[n], element_size, compare);
                commonplace_qsort(actual + prefix, counts[n], element_size, compare);
                assert(memcmp(actual + prefix, expected, bytes) == 0);
                for (size_t i = 0; i < prefix; ++i)
                    assert(actual[i] == 0xa5);
                for (size_t i = 0; i < 16; ++i)
                    assert(actual[prefix + bytes + i] == 0xa5);
                free(actual);
                free(expected);
            }
        }
    }
    return 0;
}
