#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <syslog.h>
#include <unistd.h>

#define CHECK(x)                                                                                   \
    do                                                                                             \
    {                                                                                              \
        if (!(x))                                                                                  \
        {                                                                                          \
            fprintf(stderr, "syslog lifecycle line %d: errno %d\n", __LINE__, errno);              \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)

static struct sockaddr_un address;

static int receiver(void)
{
    int fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    CHECK(fd >= 0);
    int capacity = 2048;
    CHECK(setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &capacity, sizeof(capacity)) == 0);
    struct timeval timeout = {5, 0};
    CHECK(setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) == 0);
    CHECK(bind(fd, (struct sockaddr *)&address, sizeof(address)) == 0);
    return fd;
}

static void receive_marker(int fd, const char *marker)
{
    char buffer[4096];
    ssize_t size = recvfrom(fd, buffer, sizeof(buffer) - 1, 0, NULL, NULL);
    if (size <= 0)
        fprintf(stderr, "missing syslog marker: %s\n", marker);
    CHECK(size > 0);
    buffer[size] = 0;
    CHECK(strstr(buffer, marker));
}

static void *log_until_cancelled(void *unused)
{
    (void)unused;
    for (;;)
    {
        syslog(LOG_NOTICE, "cancel-worker");
        pthread_testcancel();
    }
}

void check_syslog_lifecycle(void)
{
    address.sun_family = AF_UNIX;
    strcpy(address.sun_path, "/var/run/syslog");
    int fd = receiver();
    openlog("lifecycle", LOG_PID, LOG_USER);
    errno = ERANGE;
    syslog(LOG_NOTICE, "before-restart");
    CHECK(errno == ERANGE);
    receive_marker(fd, "before-restart");
    CHECK(close(fd) == 0 && unlink(address.sun_path) == 0);
    fd = receiver();
    syslog(LOG_NOTICE, "after-restart");
    receive_marker(fd, "after-restart");

    int sender = socket(AF_UNIX, SOCK_DGRAM, 0);
    CHECK(sender >= 0);
    CHECK(connect(sender, (struct sockaddr *)&address, sizeof(address)) == 0);
    char payload[1024] = {0};
    unsigned sent = 0;
    while (send(sender, payload, sizeof(payload), MSG_DONTWAIT) >= 0)
        CHECK(++sent < 1024);
    CHECK(errno == ENOBUFS || errno == EAGAIN);
    struct timeval before, after;
    CHECK(gettimeofday(&before, NULL) == 0);
    syslog(LOG_NOTICE, "full-receiver");
    CHECK(gettimeofday(&after, NULL) == 0);
    long elapsed = (after.tv_sec - before.tv_sec) * 1000000L + after.tv_usec - before.tv_usec;
    CHECK(elapsed >= 0 && elapsed < 1000000L);

    pthread_t worker;
    CHECK(pthread_create(&worker, NULL, log_until_cancelled, NULL) == 0);
    usleep(2000);
    pid_t child = fork();
    CHECK(child >= 0);
    if (!child)
    {
        syslog(LOG_NOTICE, "fork-with-active-logger");
        _exit(0);
    }
    int status;
    CHECK(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 0);
    CHECK(pthread_cancel(worker) == 0);
    void *result = NULL;
    CHECK(pthread_join(worker, &result) == 0 && result == PTHREAD_CANCELED);
    CHECK(close(sender) == 0);
    CHECK(fcntl(fd, F_SETFL, O_NONBLOCK) == 0);
    while (recvfrom(fd, payload, sizeof(payload), 0, NULL, NULL) >= 0)
    {
    }
    CHECK(errno == EAGAIN);
    CHECK(fcntl(fd, F_SETFL, 0) == 0);
    syslog(LOG_NOTICE, "after-cancel");
    receive_marker(fd, "after-cancel");
    closelog();
    CHECK(close(fd) == 0 && unlink(address.sun_path) == 0);
}
