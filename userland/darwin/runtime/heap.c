#include <errno.h>
#include <stdint.h>
#include <sys/mman.h>
#include <unistd.h>

/* Bash's upstream allocator requests a contiguous sbrk arena. Darwin's
 * 64-bit ABI does not provide brk; reserve an anonymous arena instead. */
#define ARENA_SIZE (128u * 1024u * 1024u)
extern void *__mmap(void *, size_t, int, int, int, off_t);
static unsigned char *arena;
static size_t position;

void *sbrk(int increment)
{
    if (!arena) {
        void *region = __mmap(0, ARENA_SIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
        if (region == MAP_FAILED)
            return MAP_FAILED;
        arena = region;
    }
    if ((increment >= 0 && (unsigned)increment > ARENA_SIZE - position) ||
        (increment < 0 && (uint64_t)-(int64_t)increment > position)) {
        errno = ENOMEM;
        return MAP_FAILED;
    }
    void *previous = arena + position;
    position = (size_t)((int64_t)position + increment);
    return previous;
}

void (*__syscall_logger)(uint32_t, uintptr_t, uintptr_t, uintptr_t, uintptr_t, uint32_t);
