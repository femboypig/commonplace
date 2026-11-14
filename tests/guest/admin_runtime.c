#include <errno.h>
#include <grp.h>
#include <pthread.h>
#include <pwd.h>
#include <security/pam_appl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <syslog.h>
#include <unistd.h>

#define CHECK(x)                                                                                   \
    do                                                                                             \
    {                                                                                              \
        if (!(x))                                                                                  \
        {                                                                                          \
            fprintf(stderr, "admin check line %d: errno %d\n", __LINE__, errno);                   \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)

static void *worker(void *argument)
{
    unsigned number = (unsigned)(size_t)argument;
    for (unsigned i = 0; i < 8; ++i)
    {
        struct passwd pw, *result = NULL;
        char buffer[4096];
        CHECK(getpwnam_r("root", &pw, buffer, sizeof(buffer), &result) == 0 && result &&
              pw.pw_uid == 0);
        CHECK(getpwuid_r(0, &pw, buffer, sizeof(buffer), &result) == 0 && result &&
              !strcmp(pw.pw_name, "root"));
        struct group group, *found = NULL;
        CHECK(getgrnam_r("wheel", &group, buffer, sizeof(buffer), &found) == 0 && found &&
              group.gr_gid == 0);
        errno = EINVAL;
        syslog(LOG_NOTICE, "worker:%u:%u %m", number, i);
    }
    return NULL;
}

static void logging(void)
{
    int fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    CHECK(fd >= 0);
    int capacity = 128 * 1024;
    CHECK(setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &capacity, sizeof(capacity)) == 0);
    struct sockaddr_un address = {0};
    address.sun_family = AF_UNIX;
    strcpy(address.sun_path, "/var/run/syslog");
    CHECK(bind(fd, (struct sockaddr *)&address, sizeof(address)) == 0);
    struct timeval timeout = {10, 0};
    CHECK(setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) == 0);
    openlog("commonplace-test", LOG_PID, LOG_USER);
    pthread_t threads[4];
    for (size_t n = 0; n < 4; ++n)
        CHECK(pthread_create(&threads[n], NULL, worker, (void *)n) == 0);
    unsigned seen[4] = {0};
    for (unsigned n = 0; n < 32; ++n)
    {
        char text[4096];
        ssize_t size = recvfrom(fd, text, sizeof(text) - 1, 0, NULL, NULL);
        if (size <= 0)
            fprintf(stderr, "syslog receiver stopped after %u messages\n", n);
        CHECK(size > 0);
        text[size] = 0;
        CHECK(!strncmp(text, "<13>", 4) && strstr(text, "commonplace-test[") &&
              strstr(text, "Invalid argument"));
        char *marker = strstr(text, "worker:");
        unsigned thread, index;
        CHECK(marker && sscanf(marker, "worker:%u:%u", &thread, &index) == 2);
        CHECK(thread < 4 && index < 8 && !(seen[thread] & (1u << index)));
        seen[thread] |= 1u << index;
    }
    for (unsigned n = 0; n < 4; ++n)
    {
        CHECK(pthread_join(threads[n], NULL) == 0);
        CHECK(seen[n] == 255);
    }
    closelog();
    CHECK(close(fd) == 0);
    CHECK(unlink(address.sun_path) == 0);
}

extern void check_syslog_lifecycle(void);

int main(void)
{
    logging();
    check_syslog_lifecycle();
    pam_handle_t *handle = NULL;
    CHECK(pam_start("commonplace-test", "root", NULL, &handle) == PAM_SUCCESS);
    CHECK(pam_set_item(handle, PAM_RUSER, "root") == PAM_SUCCESS);
    CHECK(pam_authenticate(handle, 0) == PAM_SUCCESS);
    CHECK(pam_acct_mgmt(handle, 0) == PAM_SUCCESS);
    CHECK(pam_set_item(handle, PAM_RUSER, "missing-account") == PAM_SUCCESS);
    CHECK(pam_acct_mgmt(handle, 0) != PAM_SUCCESS);
    CHECK(pam_open_session(handle, 0) != PAM_SUCCESS);
    CHECK(pam_end(handle, PAM_SUCCESS) == PAM_SUCCESS);
    CHECK(pam_start("missing-policy", "root", NULL, &handle) == PAM_SUCCESS);
    CHECK(pam_authenticate(handle, 0) != PAM_SUCCESS);
    CHECK(pam_end(handle, PAM_SUCCESS) == PAM_SUCCESS);
    CHECK(initgroups("root", 0) == 0);
    pid_t child = fork();
    CHECK(child >= 0);
    if (!child)
    {
        CHECK(setgroups(0, NULL) == 0);
        CHECK(setgid(501) == 0);
        CHECK(setuid(501) == 0);
        CHECK(pam_start("commonplace-test", "root", NULL, &handle) == PAM_SUCCESS);
        CHECK(pam_authenticate(handle, 0) != PAM_SUCCESS);
        CHECK(pam_end(handle, PAM_SUCCESS) == PAM_SUCCESS);
        CHECK(setuid(0) == -1 && errno == EPERM);
        _exit(0);
    }
    int status;
    CHECK(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 0);
    puts("native admin: reentrant accounts, syslog, PAM policy and privilege "
         "checks passed");
    return 0;
}
