#ifndef COMMONPLACE_TREE_H
#define COMMONPLACE_TREE_H

#include <stddef.h>
#include <stdint.h>

struct tree_frame {
    size_t offset;
    uint32_t properties, children;
};

struct tree {
    unsigned char *data;
    size_t used, capacity;
    struct tree_frame frames[8];
    unsigned depth;
    int failed;
};

void tree_init(struct tree *tree, void *data, size_t capacity);
void tree_begin(struct tree *tree, const char *name);
void tree_property(struct tree *tree, const char *name, const void *value, size_t size);
void tree_end(struct tree *tree);
size_t tree_size(const struct tree *tree);

#endif
