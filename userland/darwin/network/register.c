/* Register published interfaces through Apple's privileged network stack client.
 * Interface addresses and routes remain userspace configuration policy. */
#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <IONetworkStack.h>
#include <mach/mach.h>
#include <stdio.h>
#include <unistd.h>

int main(void)
{
    // XNU keeps the service root busy until kextd checks in. Wait for
    // device matching, which includes driver startup, without depending on
    // a userspace extension daemon in this built-in driver configuration.
    io_iterator_t devices = IO_OBJECT_NULL;
    // Service matching hides devices whose driver is still starting. Walk
    // the registry so those unfinished providers are included in the wait.
    kern_return_t quiet = IORegistryCreateIterator(kIOMasterPortDefault,
        kIOServicePlane, kIORegistryIterateRecursively, &devices);
    if (quiet != KERN_SUCCESS) {
        fprintf(stderr, "register-network: cannot enumerate PCI devices: 0x%x\n", quiet);
        return 1;
    }
    io_service_t device;
    while ((device = IOIteratorNext(devices))) {
        if (IOObjectConformsTo(device, "IOPCIDevice")) {
            mach_timespec_t timeout = {30, 0};
            quiet = IOServiceWaitQuiet(device, &timeout);
        }
        IOObjectRelease(device);
        if (quiet != KERN_SUCCESS) break;
    }
    IOObjectRelease(devices);
    if (quiet != KERN_SUCCESS) {
        fprintf(stderr, "register-network: device matching did not settle: 0x%x\n", quiet);
        return 1;
    }
    io_service_t service = IO_OBJECT_NULL;
    for (unsigned attempt = 0; attempt < 50; ++attempt) {
        CFMutableDictionaryRef matching = IOServiceMatching("IONetworkStack");
        if (!matching) break;
        service = IOServiceGetMatchingService(kIOMasterPortDefault, matching);
        if (service) break;
        usleep(100000);
    }
    if (!service) {
        fputs("register-network: Apple network stack is unavailable\n", stderr);
        return 1;
    }
    io_connect_t connection = IO_OBJECT_NULL;
    kern_return_t result = IOServiceOpen(service, mach_task_self(), 0, &connection);
    IOObjectRelease(service);
    if (result != KERN_SUCCESS) {
        fprintf(stderr, "register-network: cannot open network stack: 0x%x\n", result);
        return 1;
    }
    int command = kIONetworkStackRegisterInterfaceAll;
    CFNumberRef number = CFNumberCreate(kCFAllocatorDefault, kCFNumberIntType, &command);
    const void *key = CFSTR(kIONetworkStackUserCommandKey);
    const void *value = number;
    CFDictionaryRef request = number ? CFDictionaryCreate(kCFAllocatorDefault,
        &key, &value, 1, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks) : NULL;
    result = request ? IOConnectSetCFProperties(connection, request) : kIOReturnNoMemory;
    if (request) CFRelease(request);
    if (number) CFRelease(number);
    IOServiceClose(connection);
    if (result != KERN_SUCCESS) {
        fprintf(stderr, "register-network: interface registration failed: 0x%x\n", result);
        return 1;
    }
    return 0;
}
