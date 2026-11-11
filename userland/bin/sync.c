#include "syscall-numbers.h"
#include "system.h"
int main(void) { return system_call(SYS_sync, 0, 0, 0, 0, 0, 0) < 0; }
