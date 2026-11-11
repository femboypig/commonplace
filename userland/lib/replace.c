#include "syscall-numbers.h"
#include "runtime.h"

int replace_file(const char *path,const void *bytes,size_t size,unsigned mode)
{
    char temporary[1100];
    size_t length=strlen(path);
    if (length+5>=sizeof(temporary)) return -63;
    memcpy(temporary,path,length);
    memcpy(temporary+length,".tmp",5);
    int fd=(int)sys_open_mode(temporary,OPEN_WRITE|OPEN_CREATE|OPEN_EXCLUSIVE,mode&0777);
    if (fd<0) return fd;
    int error=write_all(fd,bytes,size);
    if (!error) error=(int)system_call(SYS_fsync,fd,0,0,0,0,0);
    long closed=sys_close(fd);
    if (!error && closed<0) error=(int)closed;
    if (!error) error=(int)system_call(SYS_rename,(uintptr_t)temporary,(uintptr_t)path,0,0,0,0);
    if (error) sys_unlink(temporary);
    return error;
}
