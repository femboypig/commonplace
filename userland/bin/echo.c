#include "runtime.h"
int main(int argc, char **argv)
{
    int first = 1, newline = 1;
    if (argc > 1 && !strcmp(argv[1], "-n")) { first = 2; newline = 0; }
    for (int i = first; i < argc; ++i) {
        if (i != first) print(1, " ");
        if (write_all(1, argv[i], strlen(argv[i])) < 0) return 1;
    }
    if (newline) print(1, "\n");
    return 0;
}
