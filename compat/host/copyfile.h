#ifndef COMMONPLACE_HOST_COPYFILE_H
#define COMMONPLACE_HOST_COPYFILE_H

#include <errno.h>
#include <unistd.h>

#define COPYFILE_DATA 1
#define O_SYMLINK O_NOFOLLOW

/* XNU's installfile only needs descriptor-to-descriptor data copying. */
static inline int fcopyfile(int source, int destination, void *state, int flags)
{
    char buffer[65536];
    ssize_t count;
    if (state != NULL || flags != COPYFILE_DATA) {
        errno = EINVAL;
        return -1;
    }
    for (;;) {
        count = read(source, buffer, sizeof(buffer));
        if (count < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        if (count == 0)
            return 0;
        for (ssize_t offset = 0; offset < count;) {
            ssize_t written = write(destination, buffer + offset, count - offset);
            if (written < 0) {
                if (errno == EINTR)
                    continue;
                return -1;
            }
            if (written == 0) {
                errno = EIO;
                return -1;
            }
            offset += written;
        }
    }
}

#endif
