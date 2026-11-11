#include "syscall-numbers.h"
#include "runtime.h"

long file_status(int fd,struct system_stat *status)
{ return system_call(SYS_fstat64,fd,(uintptr_t)status,0,0,0,0); }

int copy_stream(int source,int destination)
{
    char buffer[4096];
    for (;;) {
        long size=sys_read(source,buffer,sizeof(buffer));
        if (size==-4) continue;
        if (size<0) return (int)size;
        if (!size) return 0;
        int error=write_all(destination,buffer,(size_t)size);
        if (error<0) return error;
    }
}
