#include <asl.h>
#include <bootstrap.h>
#include <dispatch/dispatch.h>
#include <launch.h>
#include <mach/mach.h>
#include <notify.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <syslog.h>
#include <unistd.h>
#include <vproc.h>
#include <vproc_priv.h>

#define CHECK(condition)                                                                           \
    do                                                                                             \
    {                                                                                              \
        if (!(condition))                                                                          \
        {                                                                                          \
            fprintf(stderr, "launchd check line %d: %s\n", __LINE__, #condition);                  \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)

static void child_ok(pid_t child)
{
    int status;
    CHECK(child > 0);
    CHECK(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 0);
}

static void lookup_and_send(const char *name)
{
    mach_port_t port;
    CHECK(bootstrap_look_up(bootstrap_port, name, &port) == BOOTSTRAP_SUCCESS);
    mach_msg_header_t message = {.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_COPY_SEND, 0),
                                 .msgh_remote_port = port,
                                 .msgh_size = sizeof(message),
                                 .msgh_id = 12345};
    CHECK(mach_msg(&message, MACH_SEND_MSG | MACH_SEND_TIMEOUT, sizeof(message), 0, MACH_PORT_NULL,
                   5000, MACH_PORT_NULL) == MACH_MSG_SUCCESS);
    CHECK(mach_port_deallocate(mach_task_self(), port) == KERN_SUCCESS);
}

static void manager_and_namespace(void)
{
    int64_t manager = -1;
    CHECK(vproc_swap_integer(NULL, VPROC_GSK_MGR_PID, NULL, &manager) == NULL && manager == 1);
    launch_data_t request = launch_data_new_string(LAUNCH_KEY_GETJOBS);
    CHECK(request);
    launch_data_t jobs = launch_msg(request);
    launch_data_free(request);
    CHECK(jobs && launch_data_get_type(jobs) == LAUNCH_DATA_DICTIONARY);
    CHECK(launch_data_dict_lookup(jobs, "com.apple.notifyd"));
    CHECK(launch_data_dict_lookup(jobs, "com.apple.syslogd"));
    launch_data_free(jobs);

    char name[128];
    snprintf(name, sizeof(name), "org.commonplace.namespace.%d", getpid());
    mach_port_t port;
    CHECK(mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &port) == KERN_SUCCESS);
    CHECK(mach_port_insert_right(mach_task_self(), port, port, MACH_MSG_TYPE_MAKE_SEND) ==
          KERN_SUCCESS);
    CHECK(bootstrap_register(bootstrap_port, name, port) == BOOTSTRAP_SUCCESS);
    pid_t child = fork();
    CHECK(child >= 0);
    if (!child)
    {
        execl("/bin/launchd-check", "launchd-check", "lookup", name, NULL);
        _exit(127);
    }
    child_ok(child);
    struct
    {
        mach_msg_header_t header;
        mach_msg_trailer_t trailer;
    } message;
    CHECK(mach_msg(&message.header, MACH_RCV_MSG | MACH_RCV_TIMEOUT, 0, sizeof(message), port, 5000,
                   MACH_PORT_NULL) == MACH_MSG_SUCCESS);
    CHECK(message.header.msgh_id == 12345);
    CHECK(bootstrap_register(bootstrap_port, name, port) == BOOTSTRAP_SERVICE_ACTIVE);
    CHECK(mach_port_destroy(mach_task_self(), port) == KERN_SUCCESS);
    puts("native launchd: manager, job enumeration and cross-process Mach namespace passed");
}

static void managed_job(void)
{
    const char *label = "org.commonplace.check.job";
    launch_data_t job = launch_data_alloc(LAUNCH_DATA_DICTIONARY);
    launch_data_t arguments = launch_data_alloc(LAUNCH_DATA_ARRAY);
    CHECK(job && arguments);
    CHECK(launch_data_array_set_index(arguments, launch_data_new_string("/bin/sh"), 0));
    CHECK(launch_data_array_set_index(arguments, launch_data_new_string("-c"), 1));
    CHECK(launch_data_array_set_index(arguments, launch_data_new_string("exit 42"), 2));
    CHECK(launch_data_dict_insert(job, launch_data_new_string(label), LAUNCH_JOBKEY_LABEL));
    CHECK(launch_data_dict_insert(job, arguments, LAUNCH_JOBKEY_PROGRAMARGUMENTS));
    CHECK(launch_data_dict_insert(job, launch_data_new_bool(true), LAUNCH_JOBKEY_RUNATLOAD));
    launch_data_t request = launch_data_alloc(LAUNCH_DATA_DICTIONARY);
    CHECK(request && launch_data_dict_insert(request, job, LAUNCH_KEY_SUBMITJOB));
    launch_data_t response = launch_msg(request);
    CHECK(response && launch_data_get_type(response) == LAUNCH_DATA_ERRNO &&
          launch_data_get_errno(response) == 0);
    launch_data_free(response);
    launch_data_free(request);
    int complete = 0;
    for (unsigned attempt = 0; attempt < 100 && !complete; ++attempt)
    {
        request = launch_data_alloc(LAUNCH_DATA_DICTIONARY);
        CHECK(request &&
              launch_data_dict_insert(request, launch_data_new_string(label), LAUNCH_KEY_GETJOB));
        response = launch_msg(request);
        CHECK(response && launch_data_get_type(response) == LAUNCH_DATA_DICTIONARY);
        launch_data_t status = launch_data_dict_lookup(response, LAUNCH_JOBKEY_LASTEXITSTATUS);
        int exit_status = status ? (int)launch_data_get_integer(status) : -1;
        complete = status && WIFEXITED(exit_status) && WEXITSTATUS(exit_status) == 42;
        launch_data_free(response);
        launch_data_free(request);
        if (!complete)
            usleep(50000);
    }
    CHECK(complete);
    request = launch_data_alloc(LAUNCH_DATA_DICTIONARY);
    CHECK(request &&
          launch_data_dict_insert(request, launch_data_new_string(label), LAUNCH_KEY_REMOVEJOB));
    response = launch_msg(request);
    CHECK(response && launch_data_get_type(response) == LAUNCH_DATA_ERRNO &&
          launch_data_get_errno(response) == 0);
    launch_data_free(response);
    launch_data_free(request);
    puts("native launchd: job submission, exit-status collection and removal passed");
}

static void notifications(void)
{
    char name[128];
    snprintf(name, sizeof(name), "org.commonplace.notification.%d", getpid());
    int polling, event, changed;
    CHECK(notify_register_check(name, &polling) == NOTIFY_STATUS_OK);
    CHECK(notify_check(polling, &changed) == NOTIFY_STATUS_OK && changed);
    CHECK(notify_check(polling, &changed) == NOTIFY_STATUS_OK && !changed);
    CHECK(notify_set_state(polling, 0x123456789abcdefULL) == NOTIFY_STATUS_OK);
    uint64_t state;
    CHECK(notify_get_state(polling, &state) == NOTIFY_STATUS_OK && state == 0x123456789abcdefULL);
    dispatch_semaphore_t received = dispatch_semaphore_create(0);
    CHECK(received);
    CHECK(notify_register_dispatch(name, &event, dispatch_get_global_queue(0, 0), ^(int token) {
            (void)token;
            dispatch_semaphore_signal(received);
          }) == NOTIFY_STATUS_OK);
    pid_t child = fork();
    CHECK(child >= 0);
    if (!child)
    {
        execl("/bin/launchd-check", "launchd-check", "post", name, NULL);
        _exit(127);
    }
    child_ok(child);
    CHECK(dispatch_semaphore_wait(received, dispatch_time(DISPATCH_TIME_NOW, 10 * NSEC_PER_SEC)) ==
          0);
    CHECK(notify_check(polling, &changed) == NOTIFY_STATUS_OK && changed);
    CHECK(notify_cancel(polling) == NOTIFY_STATUS_OK);
    CHECK(notify_cancel(event) == NOTIFY_STATUS_OK);
    dispatch_release(received);
    puts("native notifyd: shared state, process delivery and dispatch callbacks passed");
}

static const char *record = "commonplace native service integration record";

static void logging(int write_record)
{
    aslclient client = asl_open("commonplace-check", "user", 0);
    CHECK(client);
    if (write_record)
    {
        CHECK(asl_log(client, NULL, ASL_LEVEL_NOTICE, "%s", record) == 0);
        openlog("commonplace-bsd-check", LOG_NDELAY, LOG_USER);
        syslog(LOG_NOTICE, "%s", "commonplace bsd service integration record");
        closelog();
    }
    aslmsg query = asl_new(ASL_TYPE_QUERY);
    CHECK(query);
    CHECK(asl_set_query(query, ASL_KEY_MSG, record, ASL_QUERY_OP_EQUAL) == 0);
    int found = 0;
    for (unsigned attempt = 0; attempt < 100 && !found; ++attempt)
    {
        aslresponse response = asl_search(client, query);
        if (response)
        {
            aslmsg message;
            while ((message = aslresponse_next(response)))
                if (asl_get(message, ASL_KEY_MSG) &&
                    strcmp(asl_get(message, ASL_KEY_MSG), record) == 0)
                    found = 1;
            aslresponse_free(response);
        }
        if (!found)
            usleep(200000);
    }
    CHECK(found);
    asl_free(query);
    asl_close(client);
    puts(write_record ? "native syslogd: Mach logging and daemon query passed"
                      : "native syslogd: cold-boot record recovery passed");
}

int main(int argc, char **argv)
{
    if (argc == 3 && strcmp(argv[1], "lookup") == 0)
    {
        lookup_and_send(argv[2]);
        return 0;
    }
    if (argc == 3 && strcmp(argv[1], "post") == 0)
    {
        CHECK(notify_post(argv[2]) == NOTIFY_STATUS_OK);
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "notify") == 0)
    {
        notifications();
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "query") == 0)
    {
        logging(0);
        return 0;
    }
    CHECK(argc == 1);
    manager_and_namespace();
    managed_job();
    notifications();
    logging(1);
    puts("native apple service integration passed");
    return 0;
}
