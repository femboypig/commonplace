#include "cf_checks.h"
#include <dispatch/dispatch.h>

static void timer_fired(CFRunLoopTimerRef timer, void *context)
{
    (void)timer;
    unsigned *count = context;
    ++*count;
    CFRunLoopStop(CFRunLoopGetCurrent());
}

void check_cf_runloop(void)
{
    __block unsigned block_count = 0;
    unsigned timer_count = 0;
    CFRunLoopRef loop = CFRunLoopGetCurrent();
    CHECK(loop != NULL);
    CFRunLoopPerformBlock(loop, kCFRunLoopDefaultMode, ^{
      ++block_count;
    });
    CFRunLoopTimerContext context = {0, &timer_count, NULL, NULL, NULL};
    CFRunLoopTimerRef timer = CFRunLoopTimerCreate(NULL, CFAbsoluteTimeGetCurrent() + 0.05, 0, 0, 0,
                                                   timer_fired, &context);
    CHECK(timer != NULL);
    CFRunLoopAddTimer(loop, timer, kCFRunLoopDefaultMode);
    CHECK(CFRunLoopRunInMode(kCFRunLoopDefaultMode, 5, false) == kCFRunLoopRunStopped);
    CHECK(block_count == 1 && timer_count == 1);
    CFRunLoopTimerInvalidate(timer);
    CFRelease(timer);
    puts("corefoundation run loop: queued blocks and Mach-backed timers passed");
}
