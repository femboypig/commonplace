#include "interrupts.h"
#include <IOKit/IOInterruptController.h>
#include <IOKit/IOMemoryDescriptor.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOKitKeys.h>
#include <IOKit/IOPlatformExpert.h>
#include <libkern/c++/OSContainers.h>
extern "C" {
#include <architecture/i386/pio.h>
#include <machine/machine_routines.h>
#include <i386/lapic.h>
}

/* q35 has one I/O APIC. Leave ISA sources masked; the bootstrap console
 * and disk use polling. PCI INTx uses level-triggered, active-low inputs. */
class CommonplaceIOAPIC : public IOInterruptController {
    OSDeclareDefaultStructors(CommonplaceIOAPIC);
    enum { VectorBase = 0x30, MaxInputs = 24, Masked = 1 << 16 };
    IOMemoryMap *mapping;
    volatile UInt32 *registers;
    unsigned count;

    UInt32 readRegister(unsigned index) {
        registers[0] = index;
        return registers[4];
    }
    void writeRegister(unsigned index, UInt32 value) {
        registers[0] = index;
        registers[4] = value;
    }
    void mask(unsigned input, bool masked) {
        IOInterruptState state = IOSimpleLockLockDisableInterrupt(controllerLock);
        unsigned reg = 0x10 + 2 * input;
        UInt32 value = readRegister(reg);
        writeRegister(reg, masked ? value | Masked : value & ~Masked);
        IOSimpleLockUnlockEnableInterrupt(controllerLock, state);
    }
    static void dispatch(void *target, void *, void *nub, int source) {
        static_cast<CommonplaceIOAPIC *>(target)->handleInterrupt(0, static_cast<IOService *>(nub), source);
    }
public:
    bool start(IOService *provider) APPLE_KEXT_OVERRIDE;
    void free() APPLE_KEXT_OVERRIDE;
    bool vectorCanBeShared(IOInterruptVectorNumber, IOInterruptVector *) APPLE_KEXT_OVERRIDE {
        return true;
    }
    int getVectorType(IOInterruptVectorNumber, IOInterruptVector *) APPLE_KEXT_OVERRIDE {
        return kIOInterruptTypeLevel;
    }
    void disableVectorHard(IOInterruptVectorNumber input, IOInterruptVector *) APPLE_KEXT_OVERRIDE {
        mask(input, true);
    }
    void enableVector(IOInterruptVectorNumber input, IOInterruptVector *) APPLE_KEXT_OVERRIDE {
        mask(input, false);
    }
    IOReturn handleInterrupt(void *, IOService *, int source) APPLE_KEXT_OVERRIDE;
};

OSDefineMetaClassAndStructors(CommonplaceIOAPIC, IOInterruptController);

bool CommonplaceIOAPIC::start(IOService *provider)
{
    if (!IOInterruptController::start(provider)) return false;
    controllerLock = IOSimpleLockAlloc();
    if (!controllerLock) return false;
    IOMemoryDescriptor *memory = IOMemoryDescriptor::withPhysicalAddress(
        0xfec00000, 4096, kIODirectionInOut);
    if (!memory) return false;
    mapping = memory->map();
    memory->release();
    if (!mapping) return false;
    registers = reinterpret_cast<volatile UInt32 *>(mapping->getVirtualAddress());
    count = ((readRegister(1) >> 16) & 0xff) + 1;
    if (count != MaxInputs) return false;
    vectors = IONew(IOInterruptVector, count);
    if (!vectors) return false;
    bzero(vectors, sizeof(*vectors) * count);
    for (unsigned i = 0; i < count; ++i) {
        vectors[i].interruptLock = IOLockAlloc();
        if (!vectors[i].interruptLock) return false;
        vectors[i].interruptDisabledSoft = 1;
        vectors[i].interruptDisabledHard = 1;
        writeRegister(0x10 + 2 * i, Masked | (1 << 15) | (1 << 13) | (VectorBase + i));
        writeRegister(0x11 + 2 * i, static_cast<UInt32>(ml_get_apicid(0)) << 24);
    }
    outb(0x21, 0xff);
    outb(0xa1, 0xff);
    const OSSymbol *name = OSSymbol::withCStringNoCopy("commonplace-ioapic");
    if (!name) return false;
    IOReturn result = getPlatform()->registerInterruptController(const_cast<OSSymbol *>(name), this);
    name->release();
    if (result != kIOReturnSuccess) return false;
    ml_install_interrupt_handler(provider, 0, this, dispatch, 0);
    IOLog("commonplace: q35 ioapic started (%u inputs)\n", count);
    return true;
}

IOReturn CommonplaceIOAPIC::handleInterrupt(void *, IOService *, int source)
{
    unsigned input = static_cast<unsigned>(source - VectorBase);
    if (input < count) {
        IOInterruptVector *vector = &vectors[input];
        vector->interruptActive = 1;
        if (vector->interruptRegistered && !vector->interruptDisabledSoft) {
            vector->handler(vector->target, vector->refCon, vector->nub, vector->source);
        } else {
            vector->interruptDisabledHard = 1;
            mask(input, true);
        }
        vector->interruptActive = 0;
    }
    lapic_end_of_interrupt();
    return input < count ? kIOReturnSuccess : kIOReturnInvalid;
}

void CommonplaceIOAPIC::free()
{
    if (vectors) {
        for (unsigned i = 0; i < count; ++i)
            if (vectors[i].interruptLock) IOLockFree(vectors[i].interruptLock);
        IODelete(vectors, IOInterruptVector, count);
    }
    if (mapping) mapping->release();
    if (controllerLock) IOSimpleLockFree(controllerLock);
    IOInterruptController::free();
}

bool commonplace_interrupts_start(IOService *provider)
{
    CommonplaceIOAPIC *controller = new CommonplaceIOAPIC;
    if (!controller) return false;
    bool attached = controller->init() && controller->attach(provider);
    bool ok = attached && controller->start(provider);
    if (attached && !ok) controller->detach(provider);
    controller->release();
    return ok;
}

IOReturn commonplace_set_interrupt(IOService *device, unsigned irq)
{
    if (irq < 16 || irq >= 24) return kIOReturnBadArgument;
    OSArray *controllers = OSArray::withCapacity(1);
    OSArray *specifiers = OSArray::withCapacity(1);
    OSSymbol *name = const_cast<OSSymbol *>(OSSymbol::withCStringNoCopy("commonplace-ioapic"));
    OSData *specifier = OSData::withBytes(&irq, sizeof(irq));
    bool ok = controllers && specifiers && name && specifier;
    if (ok) ok = controllers->setObject(name) && specifiers->setObject(specifier)
        && device->setProperty(gIOInterruptControllersKey, controllers)
        && device->setProperty(gIOInterruptSpecifiersKey, specifiers);
    if (controllers) controllers->release();
    if (specifiers) specifiers->release();
    if (name) name->release();
    if (specifier) specifier->release();
    return ok ? kIOReturnSuccess : kIOReturnNoMemory;
}
