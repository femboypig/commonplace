#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <inttypes.h>
#include <limits.h>
#include <pwd.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

extern int32_t getgrouplist_2(const char *, gid_t, gid_t **);
static volatile sig_atomic_t received;
static void handle(int signal)
{
    received = signal;
}
#define CHECK(condition)                                                                           \
    do {                                                                                           \
        if (!(condition)) {                                                                        \
            fprintf(stderr, "libc check failed at line %d: %s (errno %d)\n", __LINE__, #condition, \
                    errno);                                                                        \
            return 1;                                                                              \
        }                                                                                          \
    } while (0)

int main(void)
{
    struct stat metadata;
    errno = 0;
    CHECK(fstat(-1, &metadata) == -1 && errno == EBADF);
    CHECK(fstat(1, &metadata) == 0 && S_ISCHR(metadata.st_mode));
    for (size_t size = 1; size <= 65536; size *= 2) {
        unsigned char *memory = calloc(size, 1);
        CHECK(memory && !((uintptr_t)memory & 15));
        for (size_t i = 0; i < size; ++i)
            CHECK(memory[i] == 0);
        memset(memory, 0x5a, size);
        memory = realloc(memory, size + 17);
        CHECK(memory);
        for (size_t i = 0; i < size; ++i)
            CHECK(memory[i] == 0x5a);
        free(memory);
    }
    errno = 0;
    CHECK(calloc(SIZE_MAX, 2) == NULL && errno == ENOMEM);
    errno = 0;
    CHECK(malloc(SIZE_MAX) == NULL && errno == ENOMEM);
    char formatted[128], *end;
    CHECK(snprintf(formatted, sizeof(formatted), "%d %.2f %.2Lf", 42, 1.25, 2.5L) == 12);
    CHECK(!strcmp(formatted, "42 1.25 2.50"));
    errno = 0;
    CHECK(strtol("9223372036854775808", &end, 10) == LONG_MAX && errno == ERANGE && !*end);
    CHECK(strtod("1.25", &end) == 1.25 && !*end);
    CHECK(strtold("2.5", &end) == 2.5L && !*end);
    FILE *file = fopen("/tmp/darwin-libc-check", "w+");
    CHECK(file);
    CHECK(fprintf(file, "first\nsecond\n") == 13);
    CHECK(fflush(file) == 0 && fseek(file, 0, SEEK_SET) == 0);
    CHECK(fgets(formatted, sizeof(formatted), file) && !strcmp(formatted, "first\n"));
    CHECK(fgets(formatted, sizeof(formatted), file) && !strcmp(formatted, "second\n"));
    CHECK(fclose(file) == 0 && unlink("/tmp/darwin-libc-check") == 0);
    struct sigaction action = {0};
    action.sa_handler = handle;
    CHECK(sigaction(SIGUSR1, &action, 0) == 0);
    CHECK(kill(getpid(), SIGUSR1) == 0 && received == SIGUSR1);
    struct timeval before, after;
    struct timespec interval = {0, 20000000};
    CHECK(gettimeofday(&before, 0) == 0);
    CHECK(nanosleep(&interval, 0) == 0);
    CHECK(gettimeofday(&after, 0) == 0);
    CHECK((after.tv_sec - before.tv_sec) * 1000000 + after.tv_usec - before.tv_usec >= 20000);
    struct passwd *account = getpwuid(0);
    CHECK(account && !strcmp(account->pw_name, "root") && !strcmp(account->pw_dir, "/root"));
    CHECK(getpwnam("root") && getgrgid(0) && !strcmp(getgrgid(0)->gr_name, "wheel"));
    CHECK(getgrnam("operator") && getgrnam("operator")->gr_gid == 5);
    setpwent();
    CHECK(getpwent() && !getpwent());
    endpwent();
    CHECK(mkfifo("/tmp/darwin-fifo", 0600) == 0);
    CHECK(stat("/tmp/darwin-fifo", &metadata) == 0 && S_ISFIFO(metadata.st_mode));
    int fifo = open("/tmp/darwin-fifo", O_RDWR | O_NONBLOCK);
    CHECK(fifo >= 0 && write(fifo, "ok", 2) == 2 && read(fifo, formatted, 2) == 2);
    CHECK(!memcmp(formatted, "ok", 2) && close(fifo) == 0 && unlink("/tmp/darwin-fifo") == 0);
    CHECK(tcgetpgrp(0) == getpgrp());
    CHECK(tcsetpgrp(0, getpgrp()) == 0);
    pid_t child = fork();
    CHECK(child >= 0);
    if (!child)
        _exit(7);
    int status;
    CHECK(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 7);
    child = fork();
    CHECK(child >= 0);
    if (!child) {
        struct rlimit core = {0, 0};
        setrlimit(RLIMIT_CORE, &core);
        signal(SIGABRT, SIG_IGN);
        abort();
    }
    CHECK(waitpid(child, &status, 0) == child && WIFSIGNALED(status) &&
          WTERMSIG(status) == SIGABRT);
    status = system("exit 7");
    CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 7);
    file = popen("printf 'spawn-pipe\\n'", "r");
    CHECK(file && fgets(formatted, sizeof(formatted), file));
    CHECK(!strcmp(formatted, "spawn-pipe\n"));
    CHECK(pclose(file) == 0);
    gid_t *membership = NULL;
    int group_count = getgrouplist_2("root", 0, &membership);
    CHECK(group_count == 2 && membership[0] == 0 && membership[1] == 5);
    free(membership);
    puts("darwin libc: errno, allocation, formatting, files, signals, clock, accounts, fifo, fork "
         "and spawn passed");
    return 0;
}
