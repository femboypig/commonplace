#include <IOKit/IOLib.h>
#include <libkern/libkern.h>
extern "C" {
#include <architecture/i386/pio.h>
#include <machine/machine_routines.h>
}
#include "rtc-calendar.h"

static unsigned rtc_read(unsigned index)
{
    boolean_t interrupts = ml_set_interrupts_enabled(FALSE);
    /* q35 keeps NMI enabled; the CMOS address port is not readable. */
    outb(0x70, index);
    unsigned value = inb(0x71);
    ml_set_interrupts_enabled(interrupts);
    return value;
}

static void snapshot(commonplace_rtc_date *date)
{
    date->second = rtc_read(0); date->minute = rtc_read(2); date->hour = rtc_read(4);
    date->day = rtc_read(7); date->month = rtc_read(8); date->year = rtc_read(9);
    date->century = rtc_read(0x32); date->status = rtc_read(0x0b);
}

long commonplace_rtc_seconds(void)
{
    commonplace_rtc_date first, second;
    for (unsigned attempt = 0; attempt < 128; ++attempt) {
        if (!(rtc_read(0x0a) & 0x80)) {
            snapshot(&first);
            if (!(rtc_read(0x0a) & 0x80)) {
                snapshot(&second);
                if (!(rtc_read(0x0a) & 0x80) && !memcmp(&first, &second, sizeof(first)))
                    return commonplace_rtc_decode(&first);
            }
        }
        IODelay(10);
    }
    return 0;
}
