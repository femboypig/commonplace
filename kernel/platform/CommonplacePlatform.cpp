#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IOLib.h>
#include <libkern/libkern.h>
#include "rtc-calendar.h"
#include "interrupts.h"
#include "pci-config.h"

extern "C" {
#include <machine/machine_routines.h>
}

/*
 * Bootstrap platform for QEMU q35: one CPU, the kernel serial console and
 * the explicit QEMU IDE controller, and a bus-zero PCI host bridge.
 * ACPI sleep and secondary CPUs require their own platform support.
 */
extern int commonplace_platform_power(unsigned type);

class CommonplacePlatform : public IOPlatformExpert {
    OSDeclareDefaultStructors(CommonplacePlatform);

public:
    virtual bool start(IOService *provider) APPLE_KEXT_OVERRIDE;
    virtual IOReturn callPlatformFunction(const OSSymbol *, bool, void *, void *, void *, void *) APPLE_KEXT_OVERRIDE;
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
    if (!commonplace_pci_init()) return false;
    setProperty("platform-name", "commonplace");
    IOLog("commonplace: q35 bootstrap platform started\n");
    if (!commonplace_interrupts_start(this)) return false;
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

IOReturn CommonplacePlatform::callPlatformFunction(const OSSymbol *name, bool wait,
    void *p1, void *p2, void *p3, void *p4)
{
    if (name->isEqualTo("ResolvePCIInterrupt")) {
        unsigned slot = static_cast<unsigned>(reinterpret_cast<uintptr_t>(p2));
        unsigned pin = static_cast<unsigned>(reinterpret_cast<uintptr_t>(p3));
        // q35 slots 0..24 route INTA..INTD to PIRQ E..H. Onboard
        // devices 25..31 have programmable routes and are not exposed here.
        if (p1 != this || !p4 || slot >= 25 || pin >= 4) return kIOReturnUnsupported;
        *static_cast<UInt32 *>(p4) = 20 + ((slot + pin) & 3);
        return kIOReturnSuccess;
    }
    if (name->isEqualTo("SetDeviceInterrupts")) {
        if (!p1 || !p2 || reinterpret_cast<uintptr_t>(p3) != 1)
            return kIOReturnBadArgument;
        return commonplace_set_interrupt(static_cast<IOService *>(p1), *static_cast<UInt32 *>(p2));
    }
    return IOPlatformExpert::callPlatformFunction(name, wait, p1, p2, p3, p4);
}
