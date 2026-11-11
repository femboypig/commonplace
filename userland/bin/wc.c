#include "runtime.h"
int main(int argc, char **argv)
{
    int option = 0, argument = 1;
    if (argc > 1 && argv[1][0]=='-') {
        if (!strcmp(argv[1], "-l")) option='l';
        else if (!strcmp(argv[1], "-w")) option='w';
        else if (!strcmp(argv[1], "-c")) option='c';
        else { print(2, "usage: wc [-l|-w|-c] [file]\n"); return 2; }
        argument = 2;
    }
    if (argc > argument + 1) { print(2, "usage: wc [-l|-w|-c] [file]\n"); return 2; }
    int fd = argc > argument ? (int)sys_open(argv[argument], OPEN_READ) : 0;
    if (fd < 0) { report_error(argv[argument], fd); return 1; }
    char buffer[4096]; unsigned long bytes=0, words=0, lines=0; int word=0;
    for (;;) {
        long size = sys_read(fd, buffer, sizeof(buffer));
        if (size == -4) continue;
        if (size < 0) { report_error("wc read", size); if (fd) sys_close(fd); return 1; }
        if (!size) break;
        bytes += (unsigned long)size;
        for (long i=0; i<size; ++i) {
            char c=buffer[i]; int space=c==' ' || c=='\n' || c=='\t' || c=='\r' || c=='\f' || c=='\v';
            if (c=='\n') ++lines;
            if (!space && !word) ++words;
            word = !space;
        }
    }
    if (fd) sys_close(fd);
    if (option) print_number(1, option=='l' ? lines : option=='w' ? words : bytes);
    else { print_number(1, lines); print(1, "\t"); print_number(1, words); print(1, "\t"); print_number(1, bytes); }
    print(1, "\n"); return 0;
}
