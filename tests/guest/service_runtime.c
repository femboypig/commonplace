#include <arpa/inet.h>
#include <asl.h>
#include <asl_core.h>
#include <asl_file.h>
#include <asl_private.h>
#include <dispatch/dispatch.h>
#include <fcntl.h>
#include <mach/mach.h>
#include <mach/task_special_ports.h>
#include <netdb.h>
#include <notify.h>
#include <os/assumes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#include <uuid/uuid.h>

#define CHECK(value)                                                                               \
    do                                                                                             \
    {                                                                                              \
        if (!(value))                                                                              \
        {                                                                                          \
            fprintf(stderr, "service check %s:%d: %s\n", __FILE__, __LINE__, #value);              \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)

static unsigned diagnostics;
static bool assumption_report(const char *message)
{
    CHECK(strstr(message, "assertion failed:") != NULL);
    ++diagnostics;
    return true;
}
os_redirect_assumes(assumption_report);

static void runtime_primitives(void)
{
    volatile int failed_assumption = 0;
    CHECK(os_assumes(failed_assumption) == 0 && diagnostics == 1);
    uuid_t first, second;
    uuid_generate(first);
    uuid_generate(second);
    CHECK((first[6] & 0xf0) == 0x40 && (first[8] & 0xc0) == 0x80);
    CHECK(uuid_compare(first, second) != 0);
    puts("native runtime primitives: Mach-O diagnostic redirection and UUID generation passed");
}

static void bootstrap_fork(void)
{
    mach_port_t original, port;
    CHECK(task_get_bootstrap_port(mach_task_self(), &original) == KERN_SUCCESS);
    CHECK(mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &port) == KERN_SUCCESS);
    CHECK(mach_port_insert_right(mach_task_self(), port, port, MACH_MSG_TYPE_MAKE_SEND) ==
          KERN_SUCCESS);
    CHECK(task_set_bootstrap_port(mach_task_self(), port) == KERN_SUCCESS);
    pid_t child = fork();
    CHECK(child >= 0);
    if (child == 0)
    {
        mach_port_t inherited;
        CHECK(task_get_bootstrap_port(mach_task_self(), &inherited) == KERN_SUCCESS);
        CHECK(inherited != MACH_PORT_NULL && bootstrap_port == inherited);
        mach_msg_header_t message = {.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_COPY_SEND, 0),
                                     .msgh_size = sizeof(message),
                                     .msgh_remote_port = inherited,
                                     .msgh_id = 12345};
        CHECK(mach_msg(&message, MACH_SEND_MSG | MACH_SEND_TIMEOUT, sizeof(message), 0,
                       MACH_PORT_NULL, 1000, MACH_PORT_NULL) == MACH_MSG_SUCCESS);
        _exit(0);
    }
    CHECK(task_set_bootstrap_port(mach_task_self(), original) == KERN_SUCCESS);
    int status;
    CHECK(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 0);
    struct
    {
        mach_msg_header_t header;
        mach_msg_trailer_t trailer;
    } message;
    CHECK(mach_msg(&message.header, MACH_RCV_MSG | MACH_RCV_TIMEOUT, 0, sizeof(message), port, 1000,
                   MACH_PORT_NULL) == MACH_MSG_SUCCESS);
    CHECK(message.header.msgh_id == 12345);
    CHECK(mach_port_destroy(mach_task_self(), port) == KERN_SUCCESS);
    if (original != MACH_PORT_NULL)
        CHECK(mach_port_deallocate(mach_task_self(), original) == KERN_SUCCESS);
    puts("native bootstrap: fork refreshes the inherited task namespace");
}

static void address_lookups(void)
{
    struct addrinfo hints = {.ai_family = AF_INET,
                             .ai_socktype = SOCK_STREAM,
                             .ai_flags = AI_NUMERICHOST | AI_NUMERICSERV};
    struct addrinfo *addresses = NULL;
    CHECK(getaddrinfo("127.0.0.1", "12345", &hints, &addresses) == 0);
    CHECK(addresses && addresses->ai_family == AF_INET);
    struct sockaddr_in *v4 = (struct sockaddr_in *)addresses->ai_addr;
    CHECK(ntohs(v4->sin_port) == 12345 && ntohl(v4->sin_addr.s_addr) == INADDR_LOOPBACK);
    freeaddrinfo(addresses);
    hints.ai_family = AF_INET6;
    CHECK(getaddrinfo("::1", "4321", &hints, &addresses) == 0);
    CHECK(addresses && addresses->ai_family == AF_INET6);
    struct sockaddr_in6 *v6 = (struct sockaddr_in6 *)addresses->ai_addr;
    CHECK(ntohs(v6->sin6_port) == 4321 && IN6_IS_ADDR_LOOPBACK(&v6->sin6_addr));
    freeaddrinfo(addresses);
    hints.ai_family = AF_INET;
    hints.ai_flags = AI_NUMERICSERV;
    CHECK(getaddrinfo("localhost", "80", &hints, &addresses) == 0 && addresses);
    freeaddrinfo(addresses);
    hints.ai_flags |= AI_NUMERICHOST;
    CHECK(getaddrinfo("not-a-numeric-host", "80", &hints, &addresses) == EAI_NONAME);
    CHECK(strcmp(gai_strerror(EAI_NONAME), "Unknown error") != 0);
    puts("native address lookup: IPv4, IPv6, host files and invalid input passed");
}

static void notifications(void)
{
    int token, changed;
    CHECK(notify_register_check("self.commonplace.state", &token) == NOTIFY_STATUS_OK);
    CHECK(notify_check(token, &changed) == NOTIFY_STATUS_OK && changed == 1);
    CHECK(notify_check(token, &changed) == NOTIFY_STATUS_OK && changed == 0);
    CHECK(notify_set_state(token, 0x12345678abcdefULL) == NOTIFY_STATUS_OK);
    uint64_t state;
    CHECK(notify_get_state(token, &state) == NOTIFY_STATUS_OK && state == 0x12345678abcdefULL);
    CHECK(notify_post("self.commonplace.state") == NOTIFY_STATUS_OK);
    CHECK(notify_check(token, &changed) == NOTIFY_STATUS_OK && changed == 1);

    mach_port_t port = MACH_PORT_NULL;
    int mach_token;
    CHECK(notify_register_mach_port("self.commonplace.port", &port, 0, &mach_token) ==
          NOTIFY_STATUS_OK);
    CHECK(notify_post("self.commonplace.port") == NOTIFY_STATUS_OK);
    struct
    {
        mach_msg_header_t header;
        mach_msg_trailer_t trailer;
    } event;
    CHECK(mach_msg(&event.header, MACH_RCV_MSG | MACH_RCV_TIMEOUT, 0, sizeof(event), port, 5000,
                   MACH_PORT_NULL) == MACH_MSG_SUCCESS);
    CHECK(event.header.msgh_id == mach_token);
    CHECK(notify_cancel(mach_token) == NOTIFY_STATUS_OK);
    CHECK(notify_cancel(token) == NOTIFY_STATUS_OK);
    puts("native notify: state, polling and Mach delivery passed");
}

static void records(const char *path, int write_records)
{
    if (write_records)
    {
        int fd = open(path, O_CREAT | O_EXCL | O_RDWR, 0600);
        CHECK(fd >= 0);
        aslclient client = asl_open_from_file(dup(fd), "commonplace-check", "user");
        CHECK(client != NULL);
        for (unsigned i = 0; i < 32; ++i)
        {
            aslmsg message = asl_new(ASL_TYPE_MSG);
            CHECK(message != NULL);
            char number[16];
            snprintf(number, sizeof(number), "%u", i);
            CHECK(asl_set(message, "Sequence", number) == 0);
            CHECK(asl_set(message, "Escaped", "line one\nline two [value] \\ utf8: \xd0\xb4") == 0);
            CHECK(asl_log(client, message, ASL_LEVEL_NOTICE, "record %u", i) == 0);
            asl_free(message);
        }
        asl_close(client);
        CHECK(fsync(fd) == 0);
        CHECK(close(fd) == 0);
    }
    asl_file_t *file;
    CHECK(asl_file_open_read(path, &file) == ASL_STATUS_OK);
    for (unsigned i = 0; i < 32; ++i)
    {
        aslmsg message;
        CHECK(asl_file_fetch_next(file, &message) == ASL_STATUS_OK);
        char expected[32];
        snprintf(expected, sizeof(expected), "record %u", i);
        CHECK(strcmp(asl_get(message, ASL_KEY_MSG), expected) == 0);
        snprintf(expected, sizeof(expected), "%u", i);
        CHECK(strcmp(asl_get(message, "Sequence"), expected) == 0);
        CHECK(strcmp(asl_get(message, "Escaped"), "line one\nline two [value] \\ utf8: \xd0\xb4") ==
              0);
        CHECK(strcmp(asl_get(message, ASL_KEY_SENDER), "commonplace-check") == 0);
        asl_free(message);
    }
    aslmsg message = NULL;
    CHECK(asl_file_fetch_next(file, &message) == ASL_STATUS_INVALID_ARG);
    CHECK(asl_file_close(file) == ASL_STATUS_OK);
    puts("native asl: binary records, metadata and reopen passed");
}

int main(int argc, char **argv)
{
    CHECK(argc == 2 || argc == 3);
    if (argc == 3)
    {
        records(argv[1], 0);
        return 0;
    }
    runtime_primitives();
    bootstrap_fork();
    address_lookups();
    notifications();
    records(argv[1], 1);
    pid_t child = fork();
    CHECK(child >= 0);
    if (child == 0)
    {
        execl("/bin/service-check", argv[0], argv[1], "read", NULL);
        _exit(127);
    }
    int status;
    CHECK(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 0);
    CHECK(unlink(argv[1]) == 0);
    puts("native service runtime passed");
    return 0;
}
