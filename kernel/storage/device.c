#include "disk.h"
#include <sys/conf.h>
#include <sys/disk.h>
#include <sys/errno.h>
#include <sys/stat.h>
#include <sys/systm.h>
#include <miscfs/devfs/devfs.h>

u_int32_t commonplace_disk_sectors;
lck_mtx_t *commonplace_disk_io_lock;
static int registered;

static int disk_open(dev_t device, int flags __attribute__((unused)),
    int type __attribute__((unused)), struct proc *process __attribute__((unused)))
{ return registered && minor(device)==0 ? 0 : ENXIO; }

int commonplace_disk_flush(void)
{
    if (!registered) return 0;
    lck_mtx_lock(commonplace_disk_io_lock);
    int error=commonplace_ata_flush();
    lck_mtx_unlock(commonplace_disk_io_lock);
    return error;
}

static int disk_close(dev_t device __attribute__((unused)), int flags __attribute__((unused)),
    int type __attribute__((unused)), struct proc *process __attribute__((unused)))
{ return commonplace_disk_flush(); }

static int disk_size(dev_t device __attribute__((unused))) { return 512; }

static int disk_ioctl(dev_t device __attribute__((unused)), u_long command, caddr_t data,
    int flags __attribute__((unused)), struct proc *process __attribute__((unused)))
{
    switch (command) {
    case DKIOCGETBLOCKSIZE: case DKIOCGETPHYSICALBLOCKSIZE: *(u_int32_t *)data=512; return 0;
    case DKIOCSETBLOCKSIZE: return *(u_int32_t *)data==512 ? 0 : EINVAL;
    case DKIOCGETBLOCKCOUNT: *(u_int64_t *)data=commonplace_disk_sectors; return 0;
    case DKIOCISWRITABLE: case DKIOCISVIRTUAL: *(u_int32_t *)data=1; return 0;
    case DKIOCISSOLIDSTATE: case DKIOCGETFEATURES: *(u_int32_t *)data=0; return 0;
    case DKIOCGETMAXBLOCKCOUNTREAD: case DKIOCGETMAXBLOCKCOUNTWRITE: *(u_int64_t *)data=128; return 0;
    case DKIOCGETMAXBYTECOUNTREAD: case DKIOCGETMAXBYTECOUNTWRITE: *(u_int64_t *)data=65536; return 0;
    case DKIOCGETMAXSEGMENTCOUNTREAD: case DKIOCGETMAXSEGMENTCOUNTWRITE: *(u_int64_t *)data=1; return 0;
    case DKIOCSYNCHRONIZE: {
        dk_synchronize_t *request=(void *)data;
        if (request->options&~DK_SYNCHRONIZE_OPTION_BARRIER) return ENOTSUP;
        u_int64_t bytes=(u_int64_t)commonplace_disk_sectors*512;
        if (request->offset>bytes || request->length>bytes-request->offset) return EINVAL;
        return commonplace_disk_flush();
    }
    case DKIOCSYNCHRONIZECACHE: return commonplace_disk_flush();
    default: return ENOTTY;
    }
}

static struct bdevsw disk_switch={disk_open,disk_close,commonplace_disk_strategy,disk_ioctl,eno_dump,disk_size,D_DISK};

void commonplace_disk_init(void)
{
    if (commonplace_ata_probe(&commonplace_disk_sectors)) return;
    int major_number=bdevsw_add(-1,&disk_switch);
    if (major_number<0) { printf("commonplace: no block device slot\n"); return; }
    void *node=devfs_make_node(makedev(major_number,0),DEVFS_BLOCK,UID_ROOT,GID_OPERATOR,0600,"cp0");
    if (!node) {
        bdevsw_remove(major_number,&disk_switch);
        printf("commonplace: cannot publish disk device\n"); return;
    }
    int error=commonplace_disk_queue_start();
    if (error) {
        devfs_remove(node);
        bdevsw_remove(major_number,&disk_switch);
        printf("commonplace: disk queue initialization failed: %d\n",error); return;
    }
    registered=1;
    printf("commonplace: cp0 attached, %u sectors\n",commonplace_disk_sectors);
}
