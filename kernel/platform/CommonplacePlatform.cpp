#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IOLib.h>
#include <libkern/libkern.h>

/*
 * Bootstrap platform for QEMU q35: one CPU, the kernel serial console and
 * memory-backed storage. PCI enumeration, ACPI power management and secondary
 * CPUs require their own drivers before they can be advertised here.
 */
class CommonplacePlatform : public IOPlatformExpert {
    OSDeclareDefaultStructors(CommonplacePlatform);

public:
    virtual bool start(IOService *provider) APPLE_KEXT_OVERRIDE;
    virtual bool getModelName(char *name, int capacity) APPLE_KEXT_OVERRIDE;
    virtual bool getMachineName(char *name, int capacity) APPLE_KEXT_OVERRIDE;
};

OSDefineMetaClassAndStructors(CommonplacePlatform, IOPlatformExpert);

bool CommonplacePlatform::start(IOService *provider)
{
    if (!IOPlatformExpert::start(provider))
        return false;
    setProperty("platform-name", "commonplace");
    IOLog("commonplace: q35 bootstrap platform started\n");
    registerService();
    return true;
}

bool CommonplacePlatform::getModelName(char *name, int capacity)
{
    return capacity > 0 && strlcpy(name, "commonplace", capacity) < (size_t)capacity;
}

bool CommonplacePlatform::getMachineName(char *name, int capacity)
{
    return capacity > 0 && strlcpy(name, "commonplace q35", capacity) < (size_t)capacity;
}
