#include "runtime.h"
struct directory_entry {
    uint64_t inode, seek;
    uint16_t size, length;
    uint8_t type;
    char name[1024];
} __attribute__((packed));
_Static_assert(offsetof(struct directory_entry, name) == 21, "Darwin direntry64 ABI");
static int include_hidden;
static int list(const char *path)
{
    int fd = (int)sys_open(path, OPEN_READ | OPEN_DIRECTORY);
    if (fd == -20) {
        fd=(int)sys_open(path,OPEN_READ);
        if (fd>=0) { sys_close(fd); print(1,path); print(1,"\n"); return 0; }
    }
    if (fd < 0) { report_error(path, fd); return 1; }
    unsigned char buffer[8192] __attribute__((aligned(8)));
    int64_t position = 0;
    int status = 0;
    for (;;) {
        long size = sys_getdirentries(fd, buffer, sizeof(buffer), &position);
        if (size == -4) continue;
        if (size < 0) { report_error(path, size); status = 1; break; }
        if (!size) break;
        size_t offset = 0;
        while (offset < (size_t)size) {
            struct directory_entry *entry = (void *)(buffer + offset);
            size_t header = offsetof(struct directory_entry, name);
            if ((size_t)size - offset < header || entry->size < header + 1 ||
                entry->size > (size_t)size - offset || entry->size % 4 ||
                entry->length >= sizeof(entry->name) || entry->length >= entry->size - header ||
                entry->name[entry->length]) { print(2, "ls: invalid directory record\n"); status = 1; break; }
            if (entry->inode && (include_hidden || entry->name[0]!='.') && strcmp(entry->name, ".") && strcmp(entry->name, "..")) {
                print(1, entry->name); if (entry->type == 4) print(1, "/"); print(1, "\n");
            }
            offset += entry->size;
        }
        if (status) break;
    }
    sys_close(fd); return status;
}
int main(int argc, char **argv)
{
    int first=1;
    if (argc>1 && !strcmp(argv[1],"-a")) { include_hidden=1; first=2; }
    if (first<argc && !strcmp(argv[first],"--")) ++first;
    if (argc==first) return list(".");
    int status = 0;
    for (int i=first; i<argc; ++i) { if (argc>first+1) { print(1, argv[i]); print(1, ":\n"); } if (list(argv[i])) status=1; }
    return status;
}
