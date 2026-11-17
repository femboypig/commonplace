#ifndef COMMONPLACE_PCI_CONFIG_H
#define COMMONPLACE_PCI_CONFIG_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Bus/device/function occupy PCI mechanism 1 address bits 23..8.
 * The low byte selects the configuration register. */
int commonplace_pci_init(void);
uint32_t commonplace_pci_read32(uint32_t address);
uint16_t commonplace_pci_read16(uint32_t address);
uint8_t commonplace_pci_read8(uint32_t address);
void commonplace_pci_write32(uint32_t address, uint32_t value);
void commonplace_pci_write16(uint32_t address, uint16_t value);
void commonplace_pci_write8(uint32_t address, uint8_t value);

#ifdef __cplusplus
}
#endif
#endif
