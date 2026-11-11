#include "runtime.h"
int main(int argc, char **argv)
{
    long first = argc == 3 ? parse_unsigned(argv[1]) : 1;
    long last = argc == 2 || argc == 3 ? parse_unsigned(argv[argc - 1]) : -1;
    if (first < 0 || last < 0) { print(2, "usage: seq [first] last\n"); return 2; }
    for (long value = first; value <= last; ++value) { print_number(1, (unsigned long)value); print(1, "\n"); }
    return 0;
}
