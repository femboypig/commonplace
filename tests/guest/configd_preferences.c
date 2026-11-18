#include <SystemConfiguration/SystemConfiguration.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "preference check failed at line %d: %s (SCError=%d)\n", \
        __LINE__, #test, SCError()); \
    exit(1); } } while (0)

static const CFStringRef path = CFSTR("/Library/Preferences/SystemConfiguration/commonplace-check.plist");

static SCPreferencesRef open_preferences(void)
{
    SCPreferencesRef preferences = SCPreferencesCreate(NULL, CFSTR("commonplace preference check"), path);
    CHECK(preferences);
    return preferences;
}

static void changed(SCPreferencesRef preferences, SCPreferencesNotification type, void *context)
{
    (void)preferences;
    *(SCPreferencesNotification *)context |= type;
}

static void run_child(const char *mode, int unprivileged)
{
    pid_t child = fork();
    CHECK(child >= 0);
    if (!child) {
        if (unprivileged)
            CHECK(setgroups(0, NULL) == 0 && setgid(20) == 0 && setuid(501) == 0);
        execl("/bin/configd-check", "configd-check", mode, NULL);
        _exit(127);
    }
    int status;
    CHECK(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 0);
}

static void check_values(SCPreferencesRef preferences)
{
    CFTypeRef value = SCPreferencesGetValue(preferences, CFSTR("Probe"));
    CHECK(value && CFEqual(value, CFSTR("persisted native preference")));
    CFDictionaryRef network = SCPreferencesPathGetValue(preferences, CFSTR("/Services/test/IPv4"));
    CHECK(network && CFEqual(CFDictionaryGetValue(network, CFSTR("ConfigMethod")), CFSTR("DHCP")));
}

int check_preferences(const char *mode)
{
    SCPreferencesRef preferences = open_preferences();
    if (!strcmp(mode, "preferences-busy")) {
        CHECK(!SCPreferencesLock(preferences, false) && SCError() == kSCStatusPrefsBusy);
    } else if (!strcmp(mode, "preferences-reader")) {
        check_values(preferences);
        CHECK(SCPreferencesSetValue(preferences, CFSTR("Probe"), CFSTR("denied")));
        CHECK(!SCPreferencesCommitChanges(preferences) && SCError() == kSCStatusAccessError);
    } else if (!strcmp(mode, "preferences-read")) {
        check_values(preferences);
        CHECK(SCPreferencesGetSignature(preferences));
        puts("native preferences persisted across cold boot");
    } else {
        CHECK(!strcmp(mode, "preferences-write"));
        SCPreferencesRef observer = open_preferences();
        SCPreferencesNotification notifications = 0;
        SCPreferencesContext context = {0, &notifications, NULL, NULL, NULL};
        CHECK(SCPreferencesSetCallback(observer, changed, &context));
        CHECK(SCPreferencesScheduleWithRunLoop(observer, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode));
        CHECK(SCPreferencesLock(preferences, true));
        run_child("preferences-busy", 0);
        CHECK(SCPreferencesSetValue(preferences, CFSTR("Probe"), CFSTR("persisted native preference")));
        const void *key = CFSTR("ConfigMethod"), *value = CFSTR("DHCP");
        CFDictionaryRef network = CFDictionaryCreate(NULL, &key, &value, 1,
            &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
        CHECK(SCPreferencesPathSetValue(preferences, CFSTR("/Services/test/IPv4"), network));
        CFRelease(network);
        CHECK(SCPreferencesCommitChanges(preferences));
        CHECK(SCPreferencesApplyChanges(preferences));
        CHECK(SCPreferencesUnlock(preferences));
        SCPreferencesNotification expected = kSCPreferencesNotificationCommit | kSCPreferencesNotificationApply;
        for (unsigned attempt = 0; attempt < 50 && (notifications & expected) != expected; ++attempt)
            CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.1, true);
        CHECK((notifications & expected) == expected);
        CHECK(SCPreferencesUnscheduleFromRunLoop(observer, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode));
        CFRelease(observer);
        SCPreferencesSynchronize(preferences);
        check_values(preferences);
        run_child("preferences-reader", 1);
        puts("native preferences locking, notifications and permissions passed");
    }
    CFRelease(preferences);
    return 0;
}
