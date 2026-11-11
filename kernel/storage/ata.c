#include "ata.h"
#include <architecture/i386/pio.h>
#include <IOKit/IOLib.h>
#include <kern/clock.h>
#include <sys/errno.h>

#define ATA_DATA 0x1f0
#define ATA_COUNT 0x1f2
#define ATA_LBA 0x1f3
#define ATA_DRIVE 0x1f6
#define ATA_COMMAND 0x1f7
#define ATA_CONTROL 0x3f6
#define ATA_BUSY 0x80
#define ATA_DRQ 0x08
#define ATA_ERROR 0x21

static void settle(void)
{
    for (unsigned i=0; i<4; ++i) (void)inb(ATA_CONTROL);
}

static int wait_status(unsigned required, int completion, int check_error)
{
    u_int64_t deadline;
    clock_interval_to_deadline(2000, 1000000, &deadline);
    for (;;) {
        unsigned status=inb(ATA_CONTROL);
        if (!status || status==0xff) return ENXIO;
        if (!(status & ATA_BUSY)) {
            if (check_error && (status & ATA_ERROR)) return EIO;
            if ((status & required)==required && (!completion || !(status & ATA_DRQ))) return 0;
        }
        if (mach_absolute_time()>=deadline) return ETIMEDOUT;
        IOSleep(1);
    }
}

static void select_sector(u_int32_t sector)
{
    outb(ATA_DRIVE, 0xe0 | ((sector>>24)&15));
    settle();
    outb(ATA_COUNT,1);
    outb(ATA_LBA,sector&255);
    outb(ATA_LBA+1,(sector>>8)&255);
    outb(ATA_LBA+2,(sector>>16)&255);
}

int commonplace_ata_probe(u_int32_t *sectors)
{
    /* The dedicated piix3-ide is fixed at 00:05.0 by our QEMU machine definition. */
    outl(0xcf8,0x80002800);
    if (inl(0xcfc)!=0x70108086) return ENXIO;
    outl(0xcf8,0x80002808);
    if ((inl(0xcfc)>>8)&5) return ENOTSUP; /* Require legacy channels. */
    outl(0xcf8,0x80002804);
    outw(0xcfc,inw(0xcfc)|1);
    outb(ATA_CONTROL,2); /* Polled commands: do not generate legacy IRQs. */
    outb(ATA_DRIVE,0xa0); settle();
    outb(ATA_COUNT,0); outb(ATA_LBA,0); outb(ATA_LBA+1,0); outb(ATA_LBA+2,0);
    outb(ATA_COMMAND,0xec); settle();
    int error=wait_status(ATA_DRQ,0,1);
    if (error) return error;
    if (inb(ATA_LBA+1)||inb(ATA_LBA+2)) return ENOTSUP; /* Not ATAPI. */
    u_int16_t identity[256];
    for (unsigned i=0;i<256;++i) identity[i]=inw(ATA_DATA);
    error=wait_status(0,1,1);
    if (error) return error;
    if (!(identity[49]&(1u<<9))) return ENOTSUP;
    if ((identity[106]&0xd000)==0x5000 && (identity[117]!=256 || identity[118])) return ENOTSUP;
    *sectors=(u_int32_t)identity[60]|(u_int32_t)identity[61]<<16;
    return !*sectors || *sectors>0x10000000 ? ENOTSUP : 0;
}

int commonplace_ata_transfer(u_int32_t sector, unsigned count, void *data, int writing)
{
    unsigned char *bytes=data;
    if (sector>=0x10000000 || count>0x10000000-sector) return EINVAL;
    for (unsigned block=0; block<count; ++block) {
        int error=wait_status(0,1,0);
        if (error) return error;
        select_sector(sector+block);
        outb(ATA_COMMAND,writing ? 0x30 : 0x20); settle();
        error=wait_status(ATA_DRQ,0,1);
        if (error) return error;
        for (unsigned i=0; i<256; ++i) {
            if (writing) outw(ATA_DATA,(u_int16_t)bytes[0]|(u_int16_t)bytes[1]<<8);
            else { u_int16_t value=inw(ATA_DATA); bytes[0]=value&255; bytes[1]=value>>8; }
            bytes+=2;
        }
        error=wait_status(0,1,1);
        if (error) return error;
    }
    return 0;
}

int commonplace_ata_flush(void)
{
    int error=wait_status(0,1,0);
    if (error) return error;
    outb(ATA_DRIVE,0xe0); settle();
    outb(ATA_COMMAND,0xe7); settle();
    return wait_status(0,1,1);
}
