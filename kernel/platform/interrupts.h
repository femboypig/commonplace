#ifndef COMMONPLACE_INTERRUPTS_H
#define COMMONPLACE_INTERRUPTS_H

#include <IOKit/IOService.h>

bool commonplace_interrupts_start(IOService *provider);
IOReturn commonplace_set_interrupt(IOService *device, unsigned irq);

#endif
