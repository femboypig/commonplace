#include "disk.h"
#include <sys/conf.h>
#include <sys/errno.h>
#include <sys/uio.h>

static u_int raw_limit(buf_t buffer)
{
    minphys(buffer);
    if (buf_count(buffer) > 65536)
        buf_setcount(buffer, 65536);
    return (u_int)buf_count(buffer);
}

static int raw_transfer(dev_t device, struct uio *uio, int flags __attribute__((unused)))
{
    if (uio_offset(uio) < 0 || uio_offset(uio) % 512 || uio_resid(uio) % 512)
        return EINVAL;
    return physio(uio_isuserspace(uio) ? commonplace_disk_raw_strategy : commonplace_disk_strategy,
                  NULL, device, uio_rw(uio) == UIO_READ ? B_READ : B_WRITE, raw_limit, uio, 512);
}

static struct cdevsw raw_switch = {
    .d_read = raw_transfer,
    .d_write = raw_transfer,
    .d_stop = eno_stop,
    .d_reset = eno_reset,
    .d_select = eno_select,
    .d_mmap = eno_mmap,
    .d_strategy = eno_strat,
    .d_type = D_DISK,
};

int commonplace_disk_raw_register(int block_major, const struct bdevsw *block)
{
    raw_switch.d_open = block->d_open;
    raw_switch.d_close = block->d_close;
    raw_switch.d_ioctl = block->d_ioctl;
    return cdevsw_add_with_bdev(-1, &raw_switch, block_major);
}

void commonplace_disk_raw_unregister(int raw_major) { cdevsw_remove(raw_major, &raw_switch); }
