#ifndef COMMONPLACE_DISK_H
#define COMMONPLACE_DISK_H
#include "ata.h"
#include <sys/buf.h>
#include <kern/locks.h>
extern u_int32_t commonplace_disk_sectors;
extern lck_mtx_t *commonplace_disk_io_lock;
int commonplace_disk_queue_start(void);
void commonplace_disk_strategy(buf_t buffer);
#endif
