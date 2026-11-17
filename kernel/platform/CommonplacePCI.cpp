#include <IOKit/pci/IOPCIBridge.h>
#include <IOKit/IOLib.h>
#include "pci-config.h"

/* The upstream Apple family handles enumeration, BAR allocation and device
 * publication. Only PCI configuration mechanism 1 belongs to this platform. */
class CommonplacePCI : public IOPCIBridge {
    OSDeclareDefaultStructors(CommonplacePCI);
    static UInt32 address(IOPCIAddressSpace space, UInt8 offset) {
        return 0x80000000 | (space.bits & 0x00ffff00) | offset;
    }
public:
    bool configure(IOService *provider) APPLE_KEXT_OVERRIDE;
    UInt8 firstBusNum() APPLE_KEXT_OVERRIDE { return 0; }
    UInt8 lastBusNum() APPLE_KEXT_OVERRIDE { return 0; }
    IODeviceMemory *ioDeviceMemory() APPLE_KEXT_OVERRIDE { return 0; }
    IOPCIAddressSpace getBridgeSpace() APPLE_KEXT_OVERRIDE {
        IOPCIAddressSpace space; space.bits = 0; return space;
    }
    UInt32 configRead32(IOPCIAddressSpace, UInt8) APPLE_KEXT_OVERRIDE;
    UInt16 configRead16(IOPCIAddressSpace, UInt8) APPLE_KEXT_OVERRIDE;
    UInt8 configRead8(IOPCIAddressSpace, UInt8) APPLE_KEXT_OVERRIDE;
    void configWrite32(IOPCIAddressSpace, UInt8, UInt32) APPLE_KEXT_OVERRIDE;
    void configWrite16(IOPCIAddressSpace, UInt8, UInt16) APPLE_KEXT_OVERRIDE;
    void configWrite8(IOPCIAddressSpace, UInt8, UInt8) APPLE_KEXT_OVERRIDE;
};

OSDefineMetaClassAndStructors(CommonplacePCI, IOPCIBridge);

bool CommonplacePCI::configure(IOService *provider)
{
    IOPCIAddressSpace host; host.bits = 0;
    if (configRead32(host, 0) != 0x29c08086) return false;
    IOPCIAddressSpace lpc; lpc.bits = 0; lpc.s.deviceNum = 31;
    if (configRead32(lpc, 0) != 0x29188086) return false;
    // Route PIRQ A..H exclusively to I/O APIC inputs 16..23. In KVM,
    // leaving a legacy PIC route enabled can select the wrong GSI route.
    for (unsigned pin = 0; pin < 4; ++pin) {
        configWrite8(lpc, 0x60 + pin, 0x80);
        configWrite8(lpc, 0x68 + pin, 0x80);
    }
    /* These windows are below the q35 reserved chipset MMIO. The supported
     * machine has at most 8 GiB RAM, with low memory ending below this range. */
    if (!IOPCIBridge::configure(provider)
        || !addBridgeMemoryRange(0xc0000000, 0x3e000000, true)
        || !addBridgeIORange(0xc000, 0x3000)) return false;
    IOLog("commonplace: q35 pci host bridge started\n");
    return true;
}

UInt32 CommonplacePCI::configRead32(IOPCIAddressSpace space, UInt8 offset)
{
    if (space.es.registerNumExtended) return 0xffffffff;
    return commonplace_pci_read32(address(space, offset));
}

UInt16 CommonplacePCI::configRead16(IOPCIAddressSpace space, UInt8 offset)
{
    if (space.es.registerNumExtended) return 0xffff;
    return commonplace_pci_read16(address(space, offset));
}

UInt8 CommonplacePCI::configRead8(IOPCIAddressSpace space, UInt8 offset)
{
    if (space.es.registerNumExtended) return 0xff;
    return commonplace_pci_read8(address(space, offset));
}

void CommonplacePCI::configWrite32(IOPCIAddressSpace space, UInt8 offset, UInt32 value)
{
    if (space.es.registerNumExtended) return;
    commonplace_pci_write32(address(space, offset), value);
}

void CommonplacePCI::configWrite16(IOPCIAddressSpace space, UInt8 offset, UInt16 value)
{
    if (space.es.registerNumExtended) return;
    commonplace_pci_write16(address(space, offset), value);
}

void CommonplacePCI::configWrite8(IOPCIAddressSpace space, UInt8 offset, UInt8 value)
{
    if (space.es.registerNumExtended) return;
    commonplace_pci_write8(address(space, offset), value);
}
