#ifndef COMMONPLACE_BOOT_OPTIONS_H
#define COMMONPLACE_BOOT_OPTIONS_H
/* Return 1 for the persistent system disk, 0 for the default, -1 on invalid input. */
int boot_disk_root(const char *command_line);
#endif
