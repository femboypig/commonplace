#ifndef COMMONPLACE_PLATFORM_H
#define COMMONPLACE_PLATFORM_H

#include <stddef.h>
#include <stdint.h>

void console_init(void);
void console_write(const char *message);
void console_hex(uint32_t value);
_Noreturn void stop(const char *reason);
int random_bytes(void *destination, size_t size);
uint64_t read_tsc(void);
uint64_t bus_frequency(void);
uint32_t find_acpi(void);
_Noreturn void enter_kernel(uint32_t entry, uint32_t arguments);

#endif
