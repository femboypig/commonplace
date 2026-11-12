#include "options.h"
#include <assert.h>
#include <string.h>
int main(void)
{
    assert(boot_disk_root(0) == 0);
    assert(boot_disk_root("") == 0);
    assert(boot_disk_root("loader.elf root=cp1") == 1);
    assert(boot_disk_root("root=cp1") == 1);
    assert(boot_disk_root("loader.elf\troot=cp1 ") == 1);
    assert(boot_disk_root("/root=cp1/loader.elf") == 0);
    assert(boot_disk_root("root=cp0") == -1);
    assert(boot_disk_root("root=cp1 root=cp1") == -1);
    assert(boot_disk_root("root=cp11") == -1);
    assert(boot_disk_root("root=") == -1);
    char oversized[1025];
    memset(oversized, 'x', sizeof(oversized));
    assert(boot_disk_root(oversized) == -1);
}
