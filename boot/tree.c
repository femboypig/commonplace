#include "tree.h"

static size_t string_size(const char *value)
{
    size_t size = 1;
    while (*value++)
        ++size;
    return size;
}

static void write32(unsigned char *p, uint32_t value)
{
    for (unsigned i = 0; i < 4; ++i)
        p[i] = value >> (8 * i);
}

static unsigned char *reserve(struct tree *tree, size_t size)
{
    if (tree->failed || size > tree->capacity - tree->used) {
        tree->failed = 1;
        return NULL;
    }
    unsigned char *result = tree->data + tree->used;
    tree->used += size;
    for (size_t i = 0; i < size; ++i)
        result[i] = 0;
    return result;
}

void tree_init(struct tree *tree, void *data, size_t capacity)
{
    *tree = (struct tree){.data = data, .capacity = capacity};
}

void tree_begin(struct tree *tree, const char *name)
{
    if (tree->depth == 8 || (!tree->depth && tree->used)) {
        tree->failed = 1;
        return;
    }
    if (tree->depth)
        ++tree->frames[tree->depth - 1].children;
    size_t offset = tree->used;
    if (!reserve(tree, 8))
        return;
    tree->frames[tree->depth++] = (struct tree_frame){.offset = offset};
    tree_property(tree, "name", name, string_size(name));
}

void tree_property(struct tree *tree, const char *name, const void *value, size_t size)
{
    size_t name_size = string_size(name);
    if (!tree->depth || name_size > 32 || size > UINT32_MAX - 39 ||
        tree->frames[tree->depth - 1].children) {
        tree->failed = 1;
        return;
    }
    unsigned char *property = reserve(tree, 36 + ((size + 3) & ~(size_t)3));
    if (!property)
        return;
    for (size_t i = 0; i < name_size; ++i)
        property[i] = name[i];
    write32(property + 32, size);
    for (size_t i = 0; i < size; ++i)
        property[36 + i] = ((const unsigned char *)value)[i];
    ++tree->frames[tree->depth - 1].properties;
}

void tree_end(struct tree *tree)
{
    if (!tree->depth) {
        tree->failed = 1;
        return;
    }
    struct tree_frame *frame = &tree->frames[--tree->depth];
    write32(tree->data + frame->offset, frame->properties);
    write32(tree->data + frame->offset + 4, frame->children);
}

size_t tree_size(const struct tree *tree)
{
    return tree->failed || tree->depth ? 0 : tree->used;
}
