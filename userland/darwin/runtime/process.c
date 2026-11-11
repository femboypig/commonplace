#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void abort(void)
{
    sigset_t mask = 0;
    sigaddset(&mask, SIGABRT);
    sigprocmask(SIG_UNBLOCK, &mask, 0);
    kill(getpid(), SIGABRT);
    struct sigaction action = {0};
    action.sa_handler = SIG_DFL;
    sigemptyset(&action.sa_mask);
    sigaction(SIGABRT, &action, 0);
    sigprocmask(SIG_UNBLOCK, &mask, 0);
    kill(getpid(), SIGABRT);
    _exit(134);
}
void __assert_rtn(const char *function, const char *file, int line, const char *expression)
{
    fprintf(stderr, "assertion failed: %s (%s, %s:%d)\n", expression, function ? function : "?",
            file, line);
    abort();
}

#include <stdarg.h>
void abort_report_np(const char *format, ...)
{
    va_list arguments;
    va_start(arguments, format);
    vfprintf(stderr, format, arguments);
    va_end(arguments);
    abort();
}
