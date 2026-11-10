#include "platform.h"

static void out8(uint16_t port, uint8_t value)
{
    __asm__ volatile("outb %0, %1" : : "a"(value), "Nd"(port));
}

static uint8_t in8(uint16_t port)
{
    uint8_t value;
    __asm__ volatile("inb %1, %0" : "=a"(value) : "Nd"(port));
    return value;
}

void console_init(void)
{
    out8(0x3f9, 0);
    out8(0x3fb, 0x80);
    out8(0x3f8, 1);
    out8(0x3f9, 0);
    out8(0x3fb, 3);
    out8(0x3fa, 0xc7);
    out8(0x3fc, 3);
}

static void put(char c)
{
    for (unsigned attempt = 0; attempt < 1000000; ++attempt) {
        if (in8(0x3fd) & 0x20) {
            out8(0x3f8, c);
            return;
        }
    }
}

void console_write(const char *message)
{
    while (*message) {
        if (*message == '\n')
            put('\r');
        put(*message++);
    }
}

void console_hex(uint32_t value)
{
    char text[11] = "0x00000000";
    for (unsigned i = 0; i < 8; ++i)
        text[9 - i] = "0123456789abcdef"[(value >> (i * 4)) & 15];
    console_write(text);
}

_Noreturn void stop(const char *reason)
{
    console_write("boot stopped: ");
    console_write(reason);
    console_write("\n");
    for (;;)
        __asm__ volatile("cli; hlt");
}
