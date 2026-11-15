#include "cf_checks.h"
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

void check_cf_files(void)
{
    CFURLRef url = CFURLCreateWithFileSystemPath(NULL, CFSTR("/tmp/cf-stream-check"),
                                                 kCFURLPOSIXPathStyle, false);
    CHECK(url != NULL);
    const UInt8 payload[] = "native CoreFoundation stream\n";
    CFWriteStreamRef writer = CFWriteStreamCreateWithFile(NULL, url);
    CHECK(writer && CFWriteStreamOpen(writer));
    CHECK(CFWriteStreamWrite(writer, payload, sizeof(payload)) == sizeof(payload));
    CFWriteStreamClose(writer);
    CFRelease(writer);
    CFReadStreamRef reader = CFReadStreamCreateWithFile(NULL, url);
    CHECK(reader && CFReadStreamOpen(reader));
    UInt8 actual[128];
    CHECK(CFReadStreamRead(reader, actual, sizeof(actual)) == sizeof(payload));
    CHECK(memcmp(actual, payload, sizeof(payload)) == 0);
    CHECK(CFReadStreamRead(reader, actual, sizeof(actual)) == 0);
    CFReadStreamClose(reader);
    CFRelease(reader);
    CFRelease(url);
    CHECK(unlink("/tmp/cf-stream-check") == 0);

    url = CFURLCreateWithFileSystemPath(
        NULL, CFSTR("/System/Library/Frameworks/CoreFoundation.framework"), kCFURLPOSIXPathStyle,
        true);
    CFBundleRef bundle = CFBundleCreate(NULL, url);
    CHECK(bundle && CFEqual(CFBundleGetIdentifier(bundle), CFSTR("com.apple.CoreFoundation")));
    CHECK(CFEqual(CFBundleGetValueForInfoDictionaryKey(bundle, CFSTR("CFBundleExecutable")),
                  CFSTR("CoreFoundation")));
    CFRelease(bundle);
    CFRelease(url);

    CHECK(mkdir("/root/Library", 0700) == 0 || access("/root/Library", W_OK) == 0);
    CHECK(mkdir("/root/Library/Preferences", 0700) == 0 ||
          access("/root/Library/Preferences", W_OK) == 0);
    CFPreferencesSetValue(CFSTR("native-check"), CFSTR("stored"),
                          CFSTR("org.commonplace.runtime-check"), kCFPreferencesCurrentUser,
                          kCFPreferencesAnyHost);
    CHECK(CFPreferencesSynchronize(CFSTR("org.commonplace.runtime-check"),
                                   kCFPreferencesCurrentUser, kCFPreferencesAnyHost));
    CFPropertyListRef value =
        CFPreferencesCopyValue(CFSTR("native-check"), CFSTR("org.commonplace.runtime-check"),
                               kCFPreferencesCurrentUser, kCFPreferencesAnyHost);
    CHECK(value && CFEqual(value, CFSTR("stored")));
    CFRelease(value);
    puts("corefoundation files: streams, framework resources and preferences passed");
}

int main(void)
{
    check_cf_values();
    check_cf_runloop();
    check_cf_files();
    puts("native corefoundation passed");
    return 0;
}
