/* One-time provisioning policy; authentication and password updates use Apple tools. */
#include <errno.h>
#include <fcntl.h>
#include <pwd.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#include <util.h>

int main(void)
{
    const char *marker = "/etc/commonplace.setup-required";
    if (getuid() != 0 || geteuid() != 0)
        return 1;
    int terminal = open("/dev/console", O_RDWR | O_NOCTTY);
    if (terminal == -1 || !isatty(terminal) || login_tty(terminal) == -1 ||
        tcsetpgrp(STDIN_FILENO, getpgrp()) == -1)
    {
        perror("console terminal session");
        return 1;
    }
    int fd = open(marker, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd >= 0)
    {
        struct stat status;
        if (fstat(fd, &status) == -1 || !S_ISREG(status.st_mode) || status.st_uid != 0 ||
            status.st_nlink != 1 || (status.st_mode & 077) != 0)
            return 1;
        close(fd);
        for (;;)
        {
            struct passwd *root = getpwuid(0);
            if (!root)
                return 1;
            if (strncmp(root->pw_passwd, "$6$", 3) == 0)
                break;
            if (strcmp(root->pw_passwd, "*") != 0)
            {
                fputs("console: root account requires recovery\n", stderr);
                return 1;
            }
            puts("commonplace first boot: set the root password");
            fflush(stdout);
            pid_t child = fork();
            if (child == 0)
            {
                execl("/usr/bin/passwd", "passwd", "root", NULL);
                _exit(127);
            }
            if (child == -1)
                return 1;
            int result;
            pid_t reaped;
            do
            {
                reaped = waitpid(child, &result, 0);
            } while (reaped == -1 && errno == EINTR);
            if (reaped != child || !WIFEXITED(result) || WEXITSTATUS(result) != 0)
                return 1;
            /* Confirm the durable record before completing provisioning. */
        }
        if (unlink(marker) == -1)
            return 1;
        fd = open("/etc", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
        if (fd == -1 || fsync(fd) == -1)
            return 1;
        close(fd);
    }
    else if (errno != ENOENT)
        return 1;
    execl("/usr/bin/login", "login", NULL);
    perror("login");
    return 1;
}
