#include "runtime.h"

size_t strlen(const char *s) { size_t n = 0; while (s[n]) ++n; return n; }
int strcmp(const char *a, const char *b)
{ while (*a && *a == *b) { ++a; ++b; } return (unsigned char)*a - (unsigned char)*b; }
void *memcpy(void *to, const void *from, size_t size)
{ unsigned char *d = to; const unsigned char *s = from; for (size_t i=0;i<size;++i) d[i]=s[i]; return to; }
void *memset(void *to, int value, size_t size)
{ unsigned char *d = to; for (size_t i=0;i<size;++i) d[i]=(unsigned char)value; return to; }

int write_all(int fd, const void *buffer, size_t size)
{
    const char *bytes = buffer;
    while (size) {
        long result = sys_write(fd, bytes, size);
        if (result == -4) continue;
        if (result <= 0) return result < 0 ? (int)result : -5;
        bytes += result; size -= (size_t)result;
    }
    return 0;
}

void report_error(const char *name, long error)
{
    const char *message;
    switch (-error) {
    case 1: message="operation not permitted"; break;
    case 3: message="no such process"; break;
    case 5: message="input/output error"; break;
    case 9: message="bad file descriptor"; break;
    case 12: message="out of memory"; break;
    case 18: message="different filesystems"; break;
    case 22: message="invalid argument"; break;
    case 27: message="file too large"; break;
    case 45: message="operation not supported"; break;
    case 60: message="operation timed out"; break;
    case 63: message="path too long"; break;
    case 2: message="no such file or directory"; break;
    case 13: message="permission denied"; break;
    case 17: message="file exists"; break;
    case 20: message="not a directory"; break;
    case 21: message="is a directory"; break;
    case 28: message="no space left"; break;
    case 30: message="read-only filesystem"; break;
    case 66: message="directory not empty"; break;
    default: message="system error"; break;
    }
    print(2, name); print(2, ": "); print(2, message); print(2, " (");
    print_number(2, error < 0 ? (unsigned long)-error : (unsigned long)error); print(2, ")\n");
}

int memcmp(const void *first,const void *second,size_t size)
{
    const unsigned char *a=first,*b=second;
    for (size_t i=0;i<size;++i) if (a[i]!=b[i]) return (int)a[i]-(int)b[i];
    return 0;
}
