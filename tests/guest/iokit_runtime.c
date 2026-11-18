#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "IOKit check failed at line %d: %s\n", __LINE__, #test); \
    exit(1); } } while (0)

int main(void)
{
    const char *path = "/System/Library/Frameworks/IOKit.framework/IOKit";
    void *image = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    CHECK(image && dlsym(image, "IORegistryEntryGetRegistryEntryID"));
    CFURLRef url = CFURLCreateWithFileSystemPath(NULL,
        CFSTR("/System/Library/Frameworks/IOKit.framework"), kCFURLPOSIXPathStyle, true);
    CFBundleRef bundle = CFBundleCreate(NULL, url);
    CHECK(bundle && CFEqual(CFBundleGetIdentifier(bundle), CFSTR("com.apple.framework.IOKit")));
    CFRelease(bundle);
    CFRelease(url);

    mach_timespec_t timeout = {5, 0};
    CHECK(IOKitWaitQuiet(kIOMasterPortDefault, &timeout) == KERN_SUCCESS);

    io_registry_entry_t root = IORegistryGetRootEntry(kIOMasterPortDefault);
    CHECK(root);
    uint64_t identifier = 0;
    CHECK(IORegistryEntryGetRegistryEntryID(root, &identifier) == KERN_SUCCESS && identifier);
    CFMutableDictionaryRef properties = NULL;
    CHECK(IORegistryEntryCreateCFProperties(root, &properties, NULL, 0) == KERN_SUCCESS);
    CHECK(properties && CFGetTypeID(properties) == CFDictionaryGetTypeID());
    CFRelease(properties);
    io_iterator_t iterator;
    CHECK(IORegistryEntryCreateIterator(root, kIOServicePlane, kIORegistryIterateRecursively,
        &iterator) == KERN_SUCCESS);
    unsigned count = 0;
    io_object_t object;
    while ((object = IOIteratorNext(iterator))) {
        io_name_t name;
        CHECK(IOObjectGetClass(object, name) == KERN_SUCCESS && name[0]);
        CHECK(IOObjectRelease(object) == KERN_SUCCESS);
        CHECK(++count < 4096);
    }
    CHECK(count && IOIteratorIsValid(iterator));
    CHECK(IOObjectRelease(iterator) == KERN_SUCCESS);
    CHECK(IOObjectRelease(root) == KERN_SUCCESS);

    CHECK(IOConnectTrap0(MACH_PORT_NULL, 0) == kIOReturnBadArgument);
    CHECK(IOConnectTrap6(MACH_PORT_NULL, 0, 1, 2, 3, 4, 5, 6) == kIOReturnBadArgument);
    CHECK(dlclose(image) == 0);
    puts("native IOKit framework, registry and trap checks passed");
    return 0;
}
