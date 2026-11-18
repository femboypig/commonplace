#include <SystemConfiguration/SystemConfiguration.h>
#include <CoreFoundation/CFMachPort.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "configd check failed at line %d: %s (SCError=%d)\n", \
        __LINE__, #test, SCError()); \
    exit(1); } } while (0)

struct notification {
    CFStringRef key;
    unsigned count;
};

static void changed(SCDynamicStoreRef store, CFArrayRef keys, void *context)
{
    (void)store;
    struct notification *notification = context;
    CHECK(CFArrayContainsValue(keys, CFRangeMake(0, CFArrayGetCount(keys)), notification->key));
    ++notification->count;
}

static SCDynamicStoreRef open_store(SCDynamicStoreCallBack callback, void *context)
{
    SCDynamicStoreContext options = {0, context, NULL, NULL, NULL};
    SCDynamicStoreRef store = NULL;
    for (unsigned attempt = 0; attempt < 50 && !store; ++attempt) {
        store = SCDynamicStoreCreate(NULL, CFSTR("commonplace configd check"), callback, &options);
        if (!store) usleep(100000);
    }
    CHECK(store);
    return store;
}

static void check_notifications(SCDynamicStoreRef store, struct notification *notification)
{
    const void *key = notification->key;
    CFArrayRef keys = CFArrayCreate(NULL, &key, 1, &kCFTypeArrayCallBacks);
    CHECK(SCDynamicStoreSetNotificationKeys(store, keys, NULL));
    CFRunLoopSourceRef source = SCDynamicStoreCreateRunLoopSource(NULL, store, 0);
    CHECK(source);
    CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopDefaultMode);
    SCDynamicStoreRef writer = open_store(NULL, NULL);
    CHECK(SCDynamicStoreSetValue(writer, notification->key, CFSTR("native-state")));
    for (unsigned attempt = 0; attempt < 50 && !notification->count; ++attempt)
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.1, true);
    CHECK(notification->count);
    CFPropertyListRef value = SCDynamicStoreCopyValue(store, notification->key);
    CHECK(value && CFEqual(value, CFSTR("native-state")));
    CFRelease(value);
    CFRelease(writer);
    CFRunLoopRemoveSource(CFRunLoopGetCurrent(), source, kCFRunLoopDefaultMode);
    CFRelease(source);
    CFRelease(keys);
}

static void check_access(SCDynamicStoreRef store, CFStringRef key, const char *name)
{
    pid_t child = fork();
    CHECK(child >= 0);
    if (!child) {
        CHECK(setgroups(0, NULL) == 0 && setgid(20) == 0 && setuid(501) == 0);
        execl("/bin/configd-check", "configd-check", "reader", name, NULL);
        _exit(127);
    }
    int status;
    CHECK(waitpid(child, &status, 0) == child);
    CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 0);
    CFPropertyListRef value = SCDynamicStoreCopyValue(store, key);
    CHECK(value && CFEqual(value, CFSTR("native-state")));
    CFRelease(value);
}

static void check_session_cleanup(SCDynamicStoreRef store, CFStringRef key)
{
    int ready[2];
    CHECK(pipe(ready) == 0);
    char name[256], descriptor[32];
    CHECK(CFStringGetCString(key, name, sizeof(name), kCFStringEncodingUTF8));
    snprintf(descriptor, sizeof(descriptor), "%d", ready[1]);
    pid_t child = fork();
    CHECK(child >= 0);
    if (!child) {
        close(ready[0]);
        execl("/bin/configd-check", "configd-check", "session", name, descriptor, NULL);
        _exit(127);
    }
    close(ready[1]);
    char status;
    CHECK(read(ready[0], &status, 1) == 1 && status == '1');
    close(ready[0]);
    CFPropertyListRef value = SCDynamicStoreCopyValue(store, key);
    CHECK(value && CFEqual(value, CFSTR("session-owned")));
    CFRelease(value);
    CHECK(kill(child, SIGKILL) == 0);
    int exited;
    CHECK(waitpid(child, &exited, 0) == child && WIFSIGNALED(exited));
    for (unsigned attempt = 0; attempt < 50; ++attempt) {
        value = SCDynamicStoreCopyValue(store, key);
        if (!value) break;
        CFRelease(value);
        usleep(20000);
    }
    CHECK(!value && SCError() == kSCStatusNoKey);
}

int main(int argc, char **argv)
{
    if (argc == 4 && !strcmp(argv[1], "session")) {
        CFStringRef key = CFStringCreateWithCString(NULL, argv[2], kCFStringEncodingUTF8);
        SCDynamicStoreRef temporary = open_store(NULL, NULL);
        CHECK(SCDynamicStoreAddTemporaryValue(temporary, key, CFSTR("session-owned")));
        CHECK(write(atoi(argv[3]), "1", 1) == 1);
        for (;;) pause();
    }
    if (argc == 3 && !strcmp(argv[1], "reader")) {
        fprintf(stderr, "configd reader: uid=%d\n", getuid());
        CFStringRef key = CFStringCreateWithCString(NULL, argv[2], kCFStringEncodingUTF8);
        SCDynamicStoreRef store = open_store(NULL, NULL);
        fputs("configd reader: connected\n", stderr);
        CFPropertyListRef value = SCDynamicStoreCopyValue(store, key);
        CHECK(value && CFEqual(value, CFSTR("native-state")));
        fputs("configd reader: read state\n", stderr);
        CHECK(!SCDynamicStoreSetValue(store, key, CFSTR("denied")) && SCError() == kSCStatusAccessError);
        fputs("configd reader: write denied\n", stderr);
        CHECK(!SCDynamicStoreRemoveValue(store, key) && SCError() == kSCStatusAccessError);
        CHECK(!SCDynamicStoreNotifyValue(store, key) && SCError() == kSCStatusAccessError);
        CFRelease(value);
        CFRelease(store);
        CFRelease(key);
        return 0;
    }
    char name[128];
    snprintf(name, sizeof(name), "State:/Network/CommonplaceCheck/%d", getpid());
    CFStringRef key = CFStringCreateWithCString(NULL, name, kCFStringEncodingUTF8);
    struct notification notification = {key, 0};
    SCDynamicStoreRef store = open_store(changed, &notification);
    puts("configd checks: runloop notifications");
    check_notifications(store, &notification);
    puts("configd checks: unprivileged access");
    check_access(store, key, name);

    puts("configd checks: dead client cleanup");
    CFStringRef temporary = CFStringCreateWithFormat(NULL, NULL, CFSTR("%@/Session"), key);
    check_session_cleanup(store, temporary);
    CFRelease(temporary);
    CFArrayRef keys = SCDynamicStoreCopyKeyList(store, key);
    CHECK(keys && CFArrayGetCount(keys) == 1);
    CFDictionaryRef values = SCDynamicStoreCopyMultiple(store, keys, NULL);
    CHECK(values && CFDictionaryGetCount(values) == 1);
    CHECK(CFEqual(CFDictionaryGetValue(values, key), CFSTR("native-state")));
    CHECK(SCDynamicStoreSetMultiple(store, NULL, keys, NULL));
    CHECK(!SCDynamicStoreCopyValue(store, key) && SCError() == kSCStatusNoKey);
    CFRelease(values);
    CFRelease(keys);
    CFRelease(store);
    CFRelease(key);
    puts("native configd store, notifications, access checks and session cleanup passed");
    return 0;
}
