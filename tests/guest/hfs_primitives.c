#include "sha1mod.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/param.h>
#include <sys/utfconv.h>

#define CHECK(x)                                                                                   \
    do                                                                                             \
    {                                                                                              \
        if (!(x))                                                                                  \
        {                                                                                          \
            fprintf(stderr, "HFS primitive check line %d\n", __LINE__);                            \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)
int main(void)
{
    const char *inputs[] = {"caf\xc3\xa9", "\xea\xb0\x81", "\xe2\x84\xab", "\xe1\xba\x9e",
                            "\xf0\x9f\x99\x82"};
    const char *expected[] = {"cafe\xcc\x81", "\xe1\x84\x80\xe1\x85\xa1\xe1\x86\xa8",
                              "\xe2\x84\xab", "\xe1\xba\x9e", "\xf0\x9f\x99\x82"};
    for (unsigned i = 0; i < 5; ++i)
    {
        unsigned char output[128];
        size_t length;
        CHECK(utf8_normalizestr((const unsigned char *)inputs[i], strlen(inputs[i]), output,
                                &length, sizeof(output), UTF_DECOMPOSED) == 0);
        CHECK(length == strlen(expected[i]) && !memcmp(output, expected[i], length + 1));
    }
    unsigned char output[128];
    size_t length;
    CHECK(utf8_normalizestr((const unsigned char *)"\xc0\xaf", 2, output, &length, sizeof(output),
                            UTF_DECOMPOSED) != 0);
    CHECK(utf8_normalizestr((const unsigned char *)"\xed\xa0\x80", 3, output, &length,
                            sizeof(output), UTF_DECOMPOSED) != 0);
    const unsigned char abc[20] = {0xa9, 0x99, 0x3e, 0x36, 0x47, 0x06, 0x81, 0x6a, 0xba, 0x3e,
                                   0x25, 0x71, 0x78, 0x50, 0xc2, 0x6c, 0x9c, 0xd0, 0xd8, 0x9d};
    YSHA1_CTX hash;
    YSHA1Init(&hash);
    YSHA1Update(&hash, (const unsigned char *)"a", 1);
    YSHA1Update(&hash, (const unsigned char *)"bc", 2);
    YSHA1Final(output, &hash);
    CHECK(!memcmp(output, abc, 20));
    puts("native HFS normalization and UUID digest passed");
    return 0;
}
