#include "runtime.h"
#include "init.h"

static volatile int stopping;
static void shutdown_requested(int signal __attribute__((unused)),
    void *info __attribute__((unused)),void *context __attribute__((unused)))
{ stopping=1; }

int init_stopping(void) { return stopping; }

static void await_shutdown(void)
{
    while (stopping) sys_sleep(60);
}

int main(void)
{
    sys_signal(SIGNAL_INT,1);
    sys_signal(SIGNAL_QUIT,1);
    if (sys_handle_signal(15,shutdown_requested)<0) {
        for (;;) sys_sleep(60);
    }
    while (init_console(0) < 0) sys_sleep(1);
    print(1, "\ncommonplace init: pid ");
    print_number(1, (unsigned long)sys_getpid());
    print(1, "\n");
    init_system();
    for (;;) {
        await_shutdown();
        long child = sys_fork();
        if (!child) {
            sys_signal(15,0);
            sys_signal(SIGNAL_INT,0); sys_signal(SIGNAL_QUIT,0);
            if (init_console(1) < 0) { print(2, "init: cannot acquire console\n"); sys_exit(126); }
            char *arguments[] = {"/bin/sh", 0};
            char *environment[] = {"PATH=/bin", "HOME=/", "TERM=vt100", 0};
            long error = sys_execve(arguments[0], arguments, environment);
            report_error("/bin/sh", error);
            sys_exit(127);
        }
        if (child < 0) report_error("init fork", child);
        else {
            int status;
            long reaped;
            do { reaped = sys_wait(-1, &status, 0); } while (reaped != child && (reaped > 0 || reaped == -4));
        }
        await_shutdown();
        sys_sleep(1);
        for (int fd = 0; fd < 3; ++fd) sys_close(fd);
        while (init_console(0) < 0) sys_sleep(1);
        print(1, "commonplace init: shell exited; restarting\n");
    }
}
