#include <IOKit/IOMemoryDescriptor.h>
#include <kern/task.h>
extern "C"
{
#include "disk.h"
#include <sys/errno.h>
}

static void fail(buf_t buffer, int error)
{
    buf_setresid(buffer, buf_count(buffer));
    buf_seterror(buffer, error);
    buf_biodone(buffer);
}

extern "C" void commonplace_disk_raw_strategy(buf_t buffer)
{
    uintptr_t original = buf_dataptr(buffer);
    IODirection direction = buf_flags(buffer) & B_READ ? kIODirectionIn : kIODirectionOut;
    IOMemoryDescriptor *memory = IOMemoryDescriptor::withAddressRange(original, buf_count(buffer),
                                                                      direction, current_task());
    if (!memory)
    {
        fail(buffer, ENOMEM);
        return;
    }
    if (memory->prepare(direction) != kIOReturnSuccess)
    {
        memory->release();
        fail(buffer, EFAULT);
        return;
    }
    IOMemoryMap *mapping = memory->map(direction == kIODirectionOut ? kIOMapReadOnly : 0);
    if (!mapping)
    {
        memory->complete(direction);
        memory->release();
        fail(buffer, ENOMEM);
        return;
    }
    /* physio owns the user buffer. Keep its kernel mapping alive until the
     * queue finishes, then restore the address physio needs for vsunlock. */
    buf_setdataptr(buffer, mapping->getVirtualAddress());
    commonplace_disk_strategy(buffer);
    buf_biowait(buffer);
    buf_setdataptr(buffer, original);
    mapping->release();
    if (memory->complete(direction) != kIOReturnSuccess && !buf_error(buffer))
        buf_seterror(buffer, EIO);
    memory->release();
}
