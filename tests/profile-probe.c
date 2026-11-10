#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "InstrProfiling.h"
#include "InstrProfilingInternal.h"

extern void __llvm_profile_register_function(void *data);
extern void __llvm_profile_reset_counters(void);

int main(void)
{
    const char names[] = {'a', 'b', 0, 'c', 'd', 0};
    uint64_t counters[] = {17, 29, 41};
    __llvm_profile_data records[] = {
        {3, 2, 0x1234, names, counters},
        {3, 1, 0x5678, names + 3, counters + 2},
    };
    __llvm_profile_register_function(&records[0]);
    __llvm_profile_register_function(&records[1]);
    size_t size = __llvm_profile_get_size_for_buffer_internal(
        records, records + 2, counters, counters + 3, names, names + sizeof(names));
    size_t payload = PROFILE_HEADER_SIZE * sizeof(uint64_t) + sizeof(records)
        + sizeof(counters) + sizeof(names);
    assert(size >= payload && size % sizeof(uint64_t) == 0);
    assert(__llvm_profile_get_size_for_buffer() == size);
    unsigned char *buffer = malloc(size + 16);
    assert(buffer);
    memset(buffer, 0xa5, size + 16);
    assert(__llvm_profile_write_buffer_internal((char *)buffer, records, records + 2,
        counters, counters + 3, names, names + sizeof(names)) == 0);
    uint64_t header[PROFILE_HEADER_SIZE];
    memcpy(header, buffer, sizeof(header));
    assert(header[0] == UINT64_C(0xff6c70726f667281));
    assert(header[1] == 1 && header[2] == 2 && header[3] == 3 && header[4] == sizeof(names));
    assert(memcmp(buffer + sizeof(header), records, sizeof(records)) == 0);
    assert(memcmp(buffer + sizeof(header) + sizeof(records), counters, sizeof(counters)) == 0);
    assert(memcmp(buffer + payload - sizeof(names), names, sizeof(names)) == 0);
    for (size_t i = payload; i < size; ++i)
        assert(buffer[i] == 0);
    for (size_t i = size; i < size + 16; ++i)
        assert(buffer[i] == 0xa5);
    __llvm_profile_reset_counters();
    for (size_t i = 0; i < 3; ++i)
        assert(counters[i] == 0);
    free(buffer);
    return 0;
}
