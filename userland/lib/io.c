#include "system.h"

void print(int fd, const char *text)
{
    size_t length = 0;
    while (text[length]) ++length;
    while (length) {
        long written = sys_write(fd, text, length);
        if (written == -4) continue; /* EINTR */
        if (written <= 0) return;
        text += written;
        length -= (size_t)written;
    }
}

void print_number(int fd, unsigned long value)
{
    char digits[3 * sizeof(value) + 1];
    char *end = digits + sizeof(digits) - 1;
    *end = 0;
    do {
        *--end = '0' + value % 10;
        value /= 10;
    } while (value);
    print(fd, end);
}
