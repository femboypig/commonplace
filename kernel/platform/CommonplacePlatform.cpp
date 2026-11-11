#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IOLib.h>
#include <libkern/libkern.h>
#include "rtc-calendar.h"

extern "C" {
#include <machine/machine_routines.h>
}

/*
 * Bootstrap platform for QEMU q35: one CPU, the kernel serial console and
 * memory-backed storage and the explicit QEMU IDE controller. PCI enumeration, ACPI sleep and secondary
 * CPUs require their own drivers before they can be advertised here.
 */
extern int commonplace_platform_power(unsigned type);

class CommonplacePlatform : public IOPlatformExpert {
    OSDeclareDefaultStructors(CommonplacePlatform);

public:
    virtual bool start(IOService *provider) APPLE_KEXT_OVERRIDE;
    virtual int haltRestart(unsigned int type) APPLE_KEXT_OVERRIDE;
    virtual long getGMTTimeOfDay(void) APPLE_KEXT_OVERRIDE;
    virtual bool getModelName(char *name, int capacity) APPLE_KEXT_OVERRIDE;
    virtual bool getMachineName(char *name, int capacity) APPLE_KEXT_OVERRIDE;
};

OSDefineMetaClassAndStructors(CommonplacePlatform, IOPlatformExpert);

bool CommonplacePlatform::start(IOService *provider)
{
    if (!IOPlatformExpert::start(provider))
        return false;
    ml_init_max_cpus(1);
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
    return capacity > 0 && strlcpy(name, "x86_64", capacity) < (size_t)capacity;
}

long CommonplacePlatform::getGMTTimeOfDay(void)
{
    return commonplace_rtc_seconds();
}

int CommonplacePlatform::haltRestart(unsigned int type)
{
    if (type==kPEHaltCPU || type==kPERestartCPU || type==kPEUPSDelayHaltCPU)
        return commonplace_platform_power(type);
    return IOPlatformExpert::haltRestart(type);
}
