#include "pci-config.h"
#include <IOKit/IOLocks.h>
#include <IOKit/assert.h>
extern "C" {
#include <architecture/i386/pio.h>
}

/* CF8 selects a register globally. The bridge, bootstrap IDE driver and
 * platform power path must serialize every address/data transaction. */
static IOSimpleLock *configLock;

int commonplace_pci_init(void)
{
    if (!configLock) configLock = IOSimpleLockAlloc();
    return configLock != 0;
}

static IOInterruptState select_config(uint32_t address)
{
    assert(configLock);
    IOInterruptState state = IOSimpleLockLockDisableInterrupt(configLock);
    outl(0xcf8, 0x80000000 | (address & 0x00fffffc));
    return state;
}

uint32_t commonplace_pci_read32(uint32_t address)
{
    IOInterruptState state = select_config(address);
    uint32_t value = inl(0xcfc);
    IOSimpleLockUnlockEnableInterrupt(configLock, state);
    return value;
}

uint16_t commonplace_pci_read16(uint32_t address)
{
    IOInterruptState state = select_config(address);
    uint16_t value = inw(0xcfc + (address & 2));
    IOSimpleLockUnlockEnableInterrupt(configLock, state);
    return value;
}

uint8_t commonplace_pci_read8(uint32_t address)
{
    IOInterruptState state = select_config(address);
    uint8_t value = inb(0xcfc + (address & 3));
    IOSimpleLockUnlockEnableInterrupt(configLock, state);
    return value;
}

void commonplace_pci_write32(uint32_t address, uint32_t value)
{
    IOInterruptState state = select_config(address);
    outl(0xcfc, value);
    IOSimpleLockUnlockEnableInterrupt(configLock, state);
}

void commonplace_pci_write16(uint32_t address, uint16_t value)
{
    IOInterruptState state = select_config(address);
    outw(0xcfc + (address & 2), value);
    IOSimpleLockUnlockEnableInterrupt(configLock, state);
}

void commonplace_pci_write8(uint32_t address, uint8_t value)
{
    IOInterruptState state = select_config(address);
    outb(0xcfc + (address & 3), value);
    IOSimpleLockUnlockEnableInterrupt(configLock, state);
}
