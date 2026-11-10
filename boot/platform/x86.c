#include "platform.h"

static void cpuid(uint32_t leaf, uint32_t registers[4])
{
    __asm__ volatile("cpuid" : "=a"(registers[0]), "=b"(registers[1]),
        "=c"(registers[2]), "=d"(registers[3]) : "a"(leaf), "c"(0));
}

uint64_t bus_frequency(void)
{
    uint32_t registers[4];
    cpuid(0x40000000, registers);
    if (registers[0] < 0x40000010 || registers[0] > 0x4000ffff)
        return 0;
    cpuid(0x40000010, registers);
    return registers[0] ? (uint64_t)registers[1] * 1000 : 0;
}

uint64_t read_tsc(void)
{
    uint32_t low, high;
    __asm__ volatile("rdtsc" : "=a"(low), "=d"(high));
    return low | (uint64_t)high << 32;
}

int random_bytes(void *destination, size_t size)
{
    uint32_t registers[4];
    cpuid(1, registers);
    if (!(registers[2] & (1u << 30)))
        return 0;
    unsigned char *bytes = destination;
    while (size) {
        uint32_t value = 0;
        unsigned char ready = 0;
        for (unsigned attempt = 0; attempt < 10 && !ready; ++attempt)
            __asm__ volatile("rdrand %0; setc %1" : "=r"(value), "=qm"(ready));
        if (!ready)
            return 0;
        for (unsigned i = 0; i < 4 && size; ++i, --size)
            *bytes++ = value >> (i * 8);
    }
    return 1;
}

static int checksum(const unsigned char *data, size_t size)
{
    uint8_t sum = 0;
    for (size_t i = 0; i < size; ++i)
        sum += data[i];
    return sum == 0;
}

static uint32_t scan_acpi(uint32_t start, uint32_t end)
{
    for (uint32_t address = start; address + 20 <= end; address += 16) {
        const unsigned char *p = (const void *)(uintptr_t)address;
        const char signature[] = "RSD PTR ";
        unsigned i = 0;
        while (i < 8 && p[i] == signature[i])
            ++i;
        if (i == 8 && checksum(p, 20))
            return address;
    }
    return 0;
}

uint32_t find_acpi(void)
{
    uint32_t ebda = (uint32_t)*(volatile uint16_t *)(uintptr_t)0x40e << 4;
    uint32_t address = 0;
    if (ebda >= 0x80000 && ebda <= 0x9fc00)
        address = scan_acpi(ebda, ebda + 1024);
    return address ? address : scan_acpi(0xe0000, 0x100000);
}
