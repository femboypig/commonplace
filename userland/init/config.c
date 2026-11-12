#include "init.h"
#include "runtime.h"

static void configure_hostname(void)
{
    char name[256] = "commonplace";
    int fd = (int)sys_open("/etc/hostname", OPEN_READ);
    if (fd >= 0)
    {
        char input[256];
        long size = sys_read(fd, input, sizeof(input));
        sys_close(fd);
        if (size > 0 && size < (long)sizeof(input))
        {
            while (size && (input[size - 1] == '\n' || input[size - 1] == '\r'))
                --size;
            int valid = size > 0;
            for (long i = 0; i < size; ++i)
            {
                unsigned char c = input[i];
                if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
                      c == '-' || c == '.'))
                    valid = 0;
            }
            if (valid)
            {
                memcpy(name, input, (size_t)size);
                name[size] = 0;
            }
            else
                print(2, "init: invalid /etc/hostname; using commonplace\n");
        }
        else
            print(2, "init: cannot read /etc/hostname; using commonplace\n");
    }
    else if (fd != -2)
        report_error("/etc/hostname", fd);
    const int hostname[] = {1, 10}; /* CTL_KERN, KERN_HOSTNAME. */
    long error = sys_sysctl(hostname, 2, 0, 0, name, strlen(name));
    if (error < 0)
        report_error("hostname", error);
}

void init_system(void)
{
    configure_hostname();
    long error = mount_hfs(0, "/", 0x10000);
    if (error < 0)
        report_error("root remount", error);
    else
        print(1, "commonplace init: writable root\n");
    int disk = (int)sys_open("/dev/cp0", OPEN_RDWR);
    if (disk >= 0)
    {
        sys_close(disk);
        error = mount_hfs("/dev/cp0", "/data", 0);
        if (error < 0)
            report_error("/data mount", error);
        else
            print(1, "commonplace init: persistent /data mounted\n");
    }
}
