#ifndef COMMONPLACE_DISK_H
#define COMMONPLACE_DISK_H
#include "ata.h"
#include <kern/locks.h>
#include <sys/buf.h>
#define COMMONPLACE_DISK_COUNT 2
extern u_int32_t commonplace_disk_sectors[COMMONPLACE_DISK_COUNT];
struct bdevsw;
int commonplace_disk_raw_register(int block_major, const struct bdevsw *block);
void commonplace_disk_raw_unregister(int raw_major);
int commonplace_disk_publish(unsigned unit, int major_number);
extern lck_mtx_t *commonplace_disk_io_lock;
int commonplace_disk_queue_start(void);
void commonplace_disk_strategy(buf_t buffer);
void commonplace_disk_raw_strategy(buf_t buffer);
#endif
