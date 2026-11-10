#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef int kern_return_t;
typedef int boolean_t;
typedef void *vm_map_t;
typedef uintptr_t vm_map_offset_t;
typedef size_t vm_map_size_t;
typedef size_t vm_size_t;
typedef struct copy {
    int type;
    size_t size;
    size_t offset;
    unsigned char cpy_kdata[];
} *vm_map_copy_t;

#define KERN_SUCCESS 0
#define KERN_INVALID_ARGUMENT 1
#define KERN_RESOURCE_SHORTAGE 2
#define VM_MAP_COPY_NULL NULL
#define VM_MAP_COPY_KERNEL_BUFFER 3
#define VM_MAP_PAGE_MASK(map) 4095UL
#define vm_map_trunc_page(address, mask) ((address) & ~(mask))
#define vm_map_round_page(address, mask) (((address) + (mask)) & ~(mask))
#define kalloc(size) malloc(size)
#define kfree(pointer, size) free(pointer)
static const size_t msg_ool_size_small = 128;
static const size_t cpy_kdata_hdr_sz = offsetof(struct copy, cpy_kdata);
static int kernel, user;
static vm_map_t kernel_map = &kernel;
static int removals, removal_flags;
static kern_return_t copyinmap(vm_map_t map, uintptr_t address, void *buffer, size_t size)
{
    memcpy(buffer, (void *)address, size);
    return KERN_SUCCESS;
}

/* XNU_FLAGS */

static kern_return_t vm_map_remove(vm_map_t map, uintptr_t start, uintptr_t end, int flags)
{
    assert(start < end);
    assert((start & 4095) == 0 && (end & 4095) == 0);
    ++removals;
    removal_flags = flags;
    return KERN_SUCCESS;
}

/* XNU_COPY */

int main(void)
{
    unsigned char payload[] = {1, 2, 3, 4, 5};
    vm_map_copy_t copy;
    vm_map_t maps[] = {&user, kernel_map};
    for (unsigned int i = 0; i < 2; ++i) {
        removals = 0;
        assert(vm_map_copyin_kernel_buffer(maps[i], (uintptr_t)payload,
            sizeof(payload), 1, &copy) == KERN_SUCCESS);
        assert(removals == 1);
        assert(removal_flags & VM_MAP_REMOVE_INTERRUPTIBLE);
        assert(removal_flags & VM_MAP_REMOVE_WAIT_FOR_KWIRE);
        assert(!!(removal_flags & VM_MAP_REMOVE_KUNWIRE) == (maps[i] == kernel_map));
        assert(copy->size == sizeof(payload));
        assert(memcmp(copy->cpy_kdata, payload, sizeof(payload)) == 0);
        free(copy);
    }
    removals = 0;
    assert(vm_map_copyin_kernel_buffer(&user, (uintptr_t)payload,
        sizeof(payload), 0, &copy) == KERN_SUCCESS);
    assert(removals == 0);
    free(copy);
    return 0;
}
