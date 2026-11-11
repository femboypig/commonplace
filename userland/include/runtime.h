#ifndef COMMONPLACE_RUNTIME_H
#define COMMONPLACE_RUNTIME_H
#include "system.h"
size_t strlen(const char *);
int strcmp(const char *, const char *);
void *memcpy(void *, const void *, size_t);
void *memset(void *, int, size_t);
int path_join(char *, size_t, const char *, const char *);
int get_directory(char *, size_t);
int copy_stream(int, int);
int write_all(int, const void *, size_t);
void report_error(const char *, long);
struct system_stat {
    int32_t device;
    uint16_t mode, links;
    uint64_t inode;
    uint32_t uid,gid;
    int32_t special_device,padding;
    struct { int64_t seconds,nanoseconds; } accessed,modified,changed,created;
    int64_t size,blocks;
    int32_t block_size;
    uint32_t flags,generation,spare;
    int64_t reserved[2];
};
_Static_assert(sizeof(struct system_stat)==144,"Darwin user64_stat64 size");
_Static_assert(offsetof(struct system_stat,inode)==8,"Darwin inode field");
_Static_assert(offsetof(struct system_stat,size)==96,"Darwin file size field");
long file_status(int,struct system_stat *);
long parse_unsigned(const char *);
#endif
