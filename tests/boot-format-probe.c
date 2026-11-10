#include "image.h"
#include "tree.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void test_tree(void)
{
    unsigned char buffer[256];
    struct tree tree;
    tree_init(&tree, buffer, sizeof(buffer));
    tree_begin(&tree, "/");
    tree_property(&tree, "compatible", "ACPI", 5);
    tree_begin(&tree, "chosen");
    tree_end(&tree);
    tree_end(&tree);
    assert(tree_size(&tree) == 144);
    assert(buffer[0] == 2 && buffer[4] == 1);
    assert(!memcmp(buffer + 8, "name", 5));
    assert(buffer[40] == 2 && buffer[44] == '/');
    assert(!memcmp(buffer + 48, "compatible", 11));
    assert(buffer[80] == 5 && !memcmp(buffer + 84, "ACPI", 5));
    assert(buffer[92] == 1 && buffer[96] == 0);
    assert(!memcmp(buffer + 136, "chosen", 7));

    tree_init(&tree, buffer, 7);
    tree_begin(&tree, "/");
    assert(!tree_size(&tree));
    tree_init(&tree, buffer, sizeof(buffer));
    tree_begin(&tree, "/");
    tree_begin(&tree, "chosen");
    tree_end(&tree);
    tree_property(&tree, "late", "x", 2);
    tree_end(&tree);
    assert(!tree_size(&tree));
    tree_init(&tree, buffer, sizeof(buffer));
    tree_begin(&tree, "/");
    tree_property(&tree, "overflow", buffer, SIZE_MAX);
    tree_end(&tree);
    assert(!tree_size(&tree));
}

static void test_image(void)
{
    /* A minimal Mach-O whose entry lives in a non-executable __HIB segment. */
    uint64_t header[36] = {0};
    uint32_t *words = (uint32_t *)header;
    words[0] = 0xfeedfacf;
    words[1] = 0x1000007;
    words[3] = 2;
    words[4] = 2;
    words[5] = 256;
    words[8] = 0x19;
    words[9] = 72;
    memcpy(&words[10], "__HIB", 6);
    header[7] = 0xffffff8000100000ULL;
    header[8] = 4096;
    header[9] = 0;
    header[10] = sizeof(header);
    words[26] = 5;
    words[27] = 184;
    words[28] = 4;
    words[29] = 42;
    header[31] = 0xffffff8000100100ULL;
    struct image image;
    assert(!image_parse(header, sizeof(header), &image));
    assert(image.count == 1 && image.entry == 0x100100 && image.end == 0x101000);
    for (size_t size = 0; size < sizeof(header); ++size)
        assert(image_parse(header, size, &image));
    header[10] = 4097;
    assert(image_parse(header, sizeof(header), &image));
    header[10] = sizeof(header);
    header[31] = 0xffffff8000101000ULL;
    assert(image_parse(header, sizeof(header), &image));
    header[31] = 0xffffff8000100100ULL;
    words[9] = UINT32_MAX;
    assert(image_parse(header, sizeof(header), &image));
}

int main(void)
{
    test_tree();
    test_image();
    return 0;
}
