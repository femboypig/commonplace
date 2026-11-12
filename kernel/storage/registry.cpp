#include <IOKit/IOBSD.h>
#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IOService.h>
#include <libkern/libkern.h>
extern "C"
{
#include "disk.h"
#include <sys/errno.h>
}

/* Publish the BSD identity consumed by IOFindBSDRoot. The block driver
 * continues to own I/O; no storage-family interface is advertised here. */
extern "C" int commonplace_disk_publish(unsigned unit, int major_number)
{
    char name[8];
    snprintf(name, sizeof(name), "cp%u", unit);
    IOService *provider = IOService::getPlatform();
    IOService *disk = new IOService;
    if (!disk)
        return ENOMEM;
    if (!disk->init() || !provider)
    {
        disk->release();
        return ENXIO;
    }
    disk->setName(name);
    if (!disk->setProperty(kIOBSDNameKey, name) ||
        !disk->setProperty(kIOBSDMajorKey, (UInt64)major_number, 32) ||
        !disk->setProperty(kIOBSDMinorKey, (UInt64)unit, 32) || !disk->attach(provider))
    {
        disk->release();
        return ENOMEM;
    }
    if (!disk->start(provider))
    {
        disk->detach(provider);
        disk->release();
        return ENXIO;
    }
    disk->registerService(kIOServiceSynchronous);
    disk->release();
    return 0;
}
