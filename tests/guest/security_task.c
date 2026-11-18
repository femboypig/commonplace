#include <CoreFoundation/CoreFoundation.h>
#include <Security/SecTask.h>
#include <Security/SecTaskPriv.h>
#include <errno.h>
#include <mach/mach.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "security task check failed at line %d: %s\n", __LINE__, #test); \
    exit(1); } } while (0)

static void check_unsigned(SecTaskRef task)
{
    CHECK(task && CFGetTypeID(task) == SecTaskGetTypeID());
    CFErrorRef error = NULL;
    CFTypeRef value = SecTaskCopyValueForEntitlement(task,
        CFSTR("com.apple.SystemConfiguration.write-access"), &error);
    CHECK(!value && !error && !SecTaskEntitlementsValidated(task));
    const void *keys[] = {CFSTR("com.apple.SystemConfiguration.write-access")};
    CFArrayRef names = CFArrayCreate(NULL, keys, 1, &kCFTypeArrayCallBacks);
    CFDictionaryRef values = SecTaskCopyValuesForEntitlements(task, names, &error);
    CHECK(values && !error && CFDictionaryGetCount(values) == 0);
    CFRelease(values);
    CFRelease(names);
    CFStringRef description = CFCopyDescription(task);
    CFStringRef pid = CFStringCreateWithFormat(NULL, NULL, CFSTR("[%d]"), getpid());
    CHECK(CFStringFind(description, pid, 0).location != kCFNotFound);
    CFRelease(pid);
    CFRelease(description);
}

static void *check_thread(void *context)
{
    (void)context;
    for (unsigned iteration = 0; iteration < 32; ++iteration) {
        SecTaskRef task = SecTaskCreateFromSelf(NULL);
        check_unsigned(task);
        CFRelease(task);
    }
    return NULL;
}

static void check_identity(void)
{
    audit_token_t token;
    mach_msg_type_number_t count = TASK_AUDIT_TOKEN_COUNT;
    CHECK(task_info(mach_task_self(), TASK_AUDIT_TOKEN, (task_info_t)&token,
        &count) == KERN_SUCCESS && count == TASK_AUDIT_TOKEN_COUNT);
    SecTaskRef task = SecTaskCreateWithAuditToken(NULL, token);
    check_unsigned(task);
    CFRelease(task);

    /* A token for an earlier process generation must not name this task. */
    token.val[7] ^= 1;
    task = SecTaskCreateWithAuditToken(NULL, token);
    CHECK(task);
    CFErrorRef error = NULL;
    CHECK(!SecTaskCopyValueForEntitlement(task,
        CFSTR("com.apple.SystemConfiguration.write-access"), &error));
    CHECK(error && CFErrorGetCode(error) == ESRCH);
    CHECK(!SecTaskEntitlementsValidated(task));
    CFRelease(error);
    CFRelease(task);
}

int main(void)
{
    pthread_t threads[4];
    for (unsigned i = 0; i < 4; ++i)
        CHECK(pthread_create(&threads[i], NULL, check_thread, NULL) == 0);
    for (unsigned i = 0; i < 4; ++i)
        CHECK(pthread_join(threads[i], NULL) == 0);
    check_identity();

    pid_t child = fork();
    CHECK(child >= 0);
    if (child == 0) {
        CHECK(setgroups(0, NULL) == 0);
        CHECK(setgid(20) == 0 && setuid(501) == 0);
        check_identity();
        _exit(0);
    }
    int status;
    CHECK(waitpid(child, &status, 0) == child);
    CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 0);
    puts("native security task identity and entitlement checks passed");
    return 0;
}
