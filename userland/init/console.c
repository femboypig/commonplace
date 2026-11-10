#include "system.h"

static int equal(const char *a, const char *b)
{
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}

void console_run(int fd)
{
    char line[256];
    for (;;) {
        print(fd, "commonplace> ");
        int result = read_line(fd, line, sizeof(line));
        if (result == -2) {
            print(fd, "input exceeds 255 bytes\n");
            continue;
        }
        if (result < 0) {
            print(fd, "console read failed\n");
            return;
        }
        if (equal(line, "help"))
            print(fd, "help  pid  echo <text>\n");
        else if (equal(line, "pid")) {
            print_number(fd, (unsigned long)sys_getpid());
            print(fd, "\n");
        } else if (line[0]=='e' && line[1]=='c' && line[2]=='h' && line[3]=='o' &&
                   (line[4]==' ' || line[4]==0)) {
            print(fd, line + (line[4] ? 5 : 4));
            print(fd, "\n");
        } else if (line[0])
            print(fd, "unknown command; type help\n");
    }
}
