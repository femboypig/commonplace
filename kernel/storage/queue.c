#include "disk.h"
#include <kern/debug.h>
#include <kern/sched_prim.h>
#include <kern/thread.h>
#include <sys/conf.h>
#include <sys/errno.h>
#include <sys/systm.h>

static lck_mtx_t *queue_lock;
static buf_t head, tail;

static void transfer(buf_t buffer)
{
    size_t size = buf_count(buffer);
    daddr64_t sector = buf_blkno(buffer);
    unsigned unit = minor(buf_device(buffer));
    u_int32_t sectors = unit < COMMONPLACE_DISK_COUNT ? commonplace_disk_sectors[unit] : 0;
    int error = 0;
    buf_setresid(buffer, size);
    if (!sectors)
        error = ENXIO;
    else if (sector < 0 || size % 512 || (u_int64_t)sector > sectors ||
             size / 512 > sectors - (u_int64_t)sector)
        error = EINVAL;
    else if (size)
    {
        caddr_t bytes;
        error = buf_map(buffer, &bytes);
        if (!error)
        {
            lck_mtx_lock(commonplace_disk_io_lock);
            int writing = !(buf_flags(buffer) & B_READ);
            error = commonplace_ata_transfer(unit, (u_int32_t)sector, (unsigned)(size / 512), bytes,
                                             writing);
            if (!error && writing)
                error = commonplace_ata_flush(unit);
            lck_mtx_unlock(commonplace_disk_io_lock);
            buf_unmap(buffer);
            if (!error)
                buf_setresid(buffer, 0);
        }
    }
    if (error)
        buf_seterror(buffer, error);
    buf_biodone(buffer);
}

static void disk_worker(void *unused __attribute__((unused)),
                        wait_result_t result __attribute__((unused)))
{
    for (;;)
    {
        lck_mtx_lock(queue_lock);
        while (!head)
            lck_mtx_sleep(queue_lock, LCK_SLEEP_DEFAULT, &head, THREAD_UNINT);
        buf_t buffer = head;
        head = buf_drvdata(buffer);
        if (!head)
            tail = 0;
        buf_setdrvdata(buffer, 0);
        lck_mtx_unlock(queue_lock);
        transfer(buffer);
    }
}

int commonplace_disk_queue_start(void)
{
    lck_grp_t *group = lck_grp_alloc_init("commonplace disk", LCK_GRP_ATTR_NULL);
    if (!group)
        return ENOMEM;
    queue_lock = lck_mtx_alloc_init(group, LCK_ATTR_NULL);
    commonplace_disk_io_lock = lck_mtx_alloc_init(group, LCK_ATTR_NULL);
    if (!queue_lock || !commonplace_disk_io_lock)
        goto failed;
    thread_t worker;
    kern_return_t status = kernel_thread_start(disk_worker, 0, &worker);
    if (status != KERN_SUCCESS)
        goto failed;
    thread_deallocate(worker);
    return 0;
failed:
    if (queue_lock)
        lck_mtx_free(queue_lock, group);
    if (commonplace_disk_io_lock)
        lck_mtx_free(commonplace_disk_io_lock, group);
    lck_grp_free(group);
    queue_lock = 0;
    commonplace_disk_io_lock = 0;
    return ENOMEM;
}

void commonplace_disk_strategy(buf_t buffer)
{
    buf_setdrvdata(buffer, 0);
    lck_mtx_lock_spin(queue_lock);
    if (tail)
        buf_setdrvdata(tail, buffer);
    else
        head = buffer;
    tail = buffer;
    thread_wakeup(&head);
    lck_mtx_unlock(queue_lock);
}
