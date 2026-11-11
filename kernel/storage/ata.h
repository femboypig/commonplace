#ifndef COMMONPLACE_ATA_H
#define COMMONPLACE_ATA_H
#include <sys/types.h>
int commonplace_ata_probe(u_int32_t *sectors);
int commonplace_ata_transfer(u_int32_t sector, unsigned count, void *bytes, int writing);
int commonplace_ata_flush(void);
void commonplace_disk_init(void);
int commonplace_disk_flush(void);
#endif
