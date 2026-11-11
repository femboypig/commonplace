#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IOLib.h>
extern "C" {
#include <architecture/i386/pio.h>
#include <machine/machine_routines.h>
#include "../storage/ata.h"
}

int commonplace_platform_power(unsigned type)
{
    int error=commonplace_disk_flush();
    if (error) {
        IOLog("commonplace: refusing shutdown after disk flush failure: %d\n",error);
        return error;
    }
    if (type==kPERestartCPU) {
        IOLog("commonplace: restarting q35\n");
        ml_set_interrupts_enabled(FALSE);
        outb(0xcf9,0x02);
        outb(0xcf9,0x06);
        return -1;
    }
    /* Intel ICH9 LPC, 00:1f.0. QEMU's S5 sleep type is zero. */
    outl(0xcf8,0x8000f800);
    if (inl(0xcfc)!=0x29188086) return -1;
    outl(0xcf8,0x8000f840);
    unsigned base=inl(0xcfc)&0xff80;
    if (!base || base>0xff80) return -1;
    IOLog("commonplace: powering off q35\n");
    ml_set_interrupts_enabled(FALSE);
    unsigned value=inw(base+4);
    outw(base+4,(value&~0x1c00)|0x2000);
    return -1;
}
