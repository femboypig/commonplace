#include "options.h"
#include <stddef.h>

int boot_disk_root(const char *line)
{
    if (!line)
        return 0;
    size_t length = 0;
    while (length < 1024 && line[length])
        ++length;
    if (length == 1024)
        return -1;
    int selected = 0;
    for (size_t position = 0; position < length;)
    {
        while (position < length && (line[position] == ' ' || line[position] == '\t'))
            ++position;
        size_t begin = position;
        while (position < length && line[position] != ' ' && line[position] != '\t')
            ++position;
        size_t size = position - begin;
        const char *token = line + begin;
        if (size < 5 || token[0] != 'r' || token[1] != 'o' || token[2] != 'o' || token[3] != 't' ||
            token[4] != '=')
            continue;
        if (selected || size != 8 || token[5] != 'c' || token[6] != 'p' || token[7] != '1')
            return -1;
        selected = 1;
    }
    return selected;
}
