#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "Mach VM check failed at line %d: %s\n", __LINE__, #test); \
    exit(1); } } while (0)

static void check_read(vm_address_t source, vm_size_t length, int wide)
{
    vm_offset_t copy = 0;
    mach_msg_type_number_t count = 0;
    kern_return_t status = wide
        ? mach_vm_read(mach_task_self(), source, length, &copy, &count)
        : vm_read(mach_task_self(), source, length, &copy, &count);
    CHECK(status == KERN_SUCCESS && count == length);
    CHECK(copy > UINT32_MAX && !memcmp((void *)source, (void *)copy, length));
    CHECK(vm_deallocate(mach_task_self(), copy, count) == KERN_SUCCESS);
}

int main(void)
{
    vm_size_t size = vm_page_size * 3;
    vm_address_t source = 0, destination = 0;
    CHECK(vm_allocate(mach_task_self(), &source, size, VM_FLAGS_ANYWHERE) == KERN_SUCCESS);
    CHECK(vm_allocate(mach_task_self(), &destination, size, VM_FLAGS_ANYWHERE) == KERN_SUCCESS);
    CHECK(source > UINT32_MAX && destination > UINT32_MAX);
    for (vm_size_t i = 0; i < size; ++i)
        ((unsigned char *)source)[i] = (unsigned char)((i * 131 + i / 257) & 255);
    for (unsigned iteration = 0; iteration < 16; ++iteration) {
        check_read(source, size, 0);
        check_read(source + 37, vm_page_size + 91, 0);
        check_read(source + 37, vm_page_size + 91, 1);
    }
    CHECK(vm_write(mach_task_self(), destination + 113, source + 37, 4091) == KERN_SUCCESS);
    CHECK(!memcmp((void *)(destination + 113), (void *)(source + 37), 4091));
    vm_size_t written = 0;
    CHECK(vm_read_overwrite(mach_task_self(), source + 91, 4001,
        destination + 17, &written) == KERN_SUCCESS && written == 4001);
    CHECK(!memcmp((void *)(destination + 17), (void *)(source + 91), 4001));
    CHECK(vm_copy(mach_task_self(), source, size, destination) == KERN_SUCCESS);
    CHECK(!memcmp((void *)source, (void *)destination, size));
    CHECK(vm_deallocate(mach_task_self(), destination, size) == KERN_SUCCESS);
    CHECK(vm_deallocate(mach_task_self(), source, size) == KERN_SUCCESS);
    puts("native Mach VM aliases and wide memory transfers passed");
    return 0;
}
