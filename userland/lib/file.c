#include "syscall-numbers.h"
#include "runtime.h"

long file_status(int fd,struct system_stat *status)
{ return system_call(SYS_fstat64,fd,(uintptr_t)status,0,0,0,0); }
