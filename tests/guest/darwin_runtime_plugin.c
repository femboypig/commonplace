#include <stdint.h>

static __thread int value = 11;
static int initialized;
static unsigned destroyed;
extern void _tlv_atexit(void (*function)(void *), void *object);

__attribute__((constructor)) static void initialize(void) { initialized = 1; }
static void destroy(void *object) { __sync_fetch_and_add(&destroyed, (unsigned)(uintptr_t)object); }

int runtime_plugin_step(void) { return initialized ? ++value : -1; }
void runtime_plugin_register_destructors(void)
{
    for (unsigned i = 0; i < 64; ++i)
        _tlv_atexit(destroy, (void *)(uintptr_t)1);
}
unsigned runtime_plugin_destroyed(void) { return destroyed; }
