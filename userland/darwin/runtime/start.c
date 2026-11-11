#include <errno.h>
#include <mach/mach.h>
#include <mach/mach_traps.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
extern long commonplace_set_tsd(void *);
extern void __atexit_init(void);
extern void __xlocale_init(void);
extern void commonplace_init_fork(void);
extern int main(int, char **, char **);
/* All programs in this profile use the UNIX03 interfaces. */
int __unix_conforming = 1;
int NXArgc;
char **NXArgv, **environ, *__progname;
static uintptr_t tsd[1024];

_Noreturn void commonplace_darwin_start(uintptr_t *stack)
{
    /* The x86_64 thread_set_tsd_base trap returns USER_CTHREAD on success. */
    if (commonplace_set_tsd(tsd) != 0x0f)
        _exit(126);
    mach_task_self_ = task_self_trap();
    vm_page_size = (vm_size_t)getpagesize();
    vm_page_mask = vm_page_size - 1;
    vm_page_shift = 0;
    for (vm_size_t size = vm_page_size; size > 1; size >>= 1)
        ++vm_page_shift;
    NXArgc = (int)stack[0];
    NXArgv = (char **)(stack + 1);
    environ = NXArgv + NXArgc + 1;
    __progname = NXArgv[0];
    char *slash = strrchr(__progname, '/');
    if (slash)
        __progname = slash + 1;
    __atexit_init();
    __xlocale_init();
    commonplace_init_fork();
    exit(main(NXArgc, NXArgv, environ));
}
