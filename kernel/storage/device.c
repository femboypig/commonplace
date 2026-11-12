#include "disk.h"
#include <miscfs/devfs/devfs.h>
#include <sys/conf.h>
#include <sys/disk.h>
#include <sys/errno.h>
#include <sys/stat.h>
#include <sys/systm.h>

u_int32_t commonplace_disk_sectors[COMMONPLACE_DISK_COUNT];
lck_mtx_t *commonplace_disk_io_lock;
static int registered;

static int disk_open(dev_t device, int flags __attribute__((unused)),
                     int type __attribute__((unused)), struct proc *process __attribute__((unused)))
{
    return registered && minor(device) < COMMONPLACE_DISK_COUNT &&
                   commonplace_disk_sectors[minor(device)]
               ? 0
               : ENXIO;
}

static int flush_unit(unsigned unit)
{
    if (!registered || unit >= COMMONPLACE_DISK_COUNT || !commonplace_disk_sectors[unit])
        return ENXIO;
    lck_mtx_lock(commonplace_disk_io_lock);
    int error = commonplace_ata_flush(unit);
    lck_mtx_unlock(commonplace_disk_io_lock);
    return error;
}

int commonplace_disk_flush(void)
{
    int first_error = 0;
    for (unsigned unit = 0; registered && unit < COMMONPLACE_DISK_COUNT; ++unit)
    {
        if (!commonplace_disk_sectors[unit])
            continue;
        int error = flush_unit(unit);
        if (error && !first_error)
            first_error = error;
    }
    return first_error;
}

static int disk_close(dev_t device, int flags __attribute__((unused)),
                      int type __attribute__((unused)),
                      struct proc *process __attribute__((unused)))
{
    return flush_unit(minor(device));
}

static int disk_size(dev_t device __attribute__((unused))) { return 512; }

static int disk_ioctl(dev_t device, u_long command, caddr_t data, int flags __attribute__((unused)),
                      struct proc *process __attribute__((unused)))
{
    unsigned unit = minor(device);
    if (unit >= COMMONPLACE_DISK_COUNT || !commonplace_disk_sectors[unit])
        return ENXIO;
    switch (command)
    {
    case DKIOCGETBLOCKSIZE:
    case DKIOCGETPHYSICALBLOCKSIZE:
        *(u_int32_t *)data = 512;
        return 0;
    case DKIOCSETBLOCKSIZE:
        return *(u_int32_t *)data == 512 ? 0 : EINVAL;
    case DKIOCGETBLOCKCOUNT:
        *(u_int64_t *)data = commonplace_disk_sectors[unit];
        return 0;
    case DKIOCISWRITABLE:
    case DKIOCISVIRTUAL:
        *(u_int32_t *)data = 1;
        return 0;
    case DKIOCISSOLIDSTATE:
    case DKIOCGETFEATURES:
        *(u_int32_t *)data = 0;
        return 0;
    case DKIOCGETMAXBLOCKCOUNTREAD:
    case DKIOCGETMAXBLOCKCOUNTWRITE:
        *(u_int64_t *)data = 128;
        return 0;
    case DKIOCGETMAXBYTECOUNTREAD:
    case DKIOCGETMAXBYTECOUNTWRITE:
        *(u_int64_t *)data = 65536;
        return 0;
    case DKIOCGETMAXSEGMENTCOUNTREAD:
    case DKIOCGETMAXSEGMENTCOUNTWRITE:
        *(u_int64_t *)data = 1;
        return 0;
    case DKIOCSYNCHRONIZE:
    {
        dk_synchronize_t *request = (void *)data;
        if (request->options & ~DK_SYNCHRONIZE_OPTION_BARRIER)
            return ENOTSUP;
        u_int64_t bytes = (u_int64_t)commonplace_disk_sectors[unit] * 512;
        if (request->offset > bytes || request->length > bytes - request->offset)
            return EINVAL;
        return flush_unit(unit);
    }
    case DKIOCSYNCHRONIZECACHE:
        return flush_unit(unit);
    default:
        return ENOTTY;
    }
}

static struct bdevsw disk_switch = {
    disk_open, disk_close, commonplace_disk_strategy, disk_ioctl, eno_dump, disk_size, D_DISK};

void commonplace_disk_init(void)
{
    unsigned found = 0;
    for (unsigned unit = 0; unit < COMMONPLACE_DISK_COUNT; ++unit)
        if (!commonplace_ata_probe(unit, &commonplace_disk_sectors[unit]))
            ++found;
        else
            commonplace_disk_sectors[unit] = 0;
    if (!found)
        return;
    int major_number = bdevsw_add(-1, &disk_switch);
    if (major_number < 0)
    {
        printf("commonplace: no block device slot\n");
        return;
    }
    int error = commonplace_disk_queue_start();
    if (error)
    {
        bdevsw_remove(major_number, &disk_switch);
        printf("commonplace: disk queue initialization failed: %d\n", error);
        return;
    }
    registered = 1;
    for (unsigned unit = 0; unit < COMMONPLACE_DISK_COUNT; ++unit)
    {
        if (!commonplace_disk_sectors[unit])
            continue;
        void *node = devfs_make_node(makedev(major_number, unit), DEVFS_BLOCK, UID_ROOT,
                                     GID_OPERATOR, 0600, "cp%u", unit);
        if (!node || commonplace_disk_publish(unit, major_number))
        {
            if (node)
                devfs_remove(node);
            commonplace_disk_sectors[unit] = 0;
            printf("commonplace: cannot publish cp%u\n", unit);
            continue;
        }
        printf("commonplace: cp%u attached, %u sectors\n", unit, commonplace_disk_sectors[unit]);
    }
}
