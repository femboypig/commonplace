#include "dispatch_checks.h"
#include <signal.h>
#include <string.h>
#include <unistd.h>

void check_dispatch_sources(void)
{
    dispatch_queue_t queue = dispatch_queue_create("commonplace.events", NULL);
    dispatch_semaphore_t completed = dispatch_semaphore_create(0);
    CHECK(queue && completed);
    dispatch_source_t timer = dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER, 0, 0, queue);
    CHECK(timer);
    __block unsigned ticks = 0;
    dispatch_source_set_timer(timer, dispatch_time(DISPATCH_TIME_NOW, NSEC_PER_MSEC),
                              10 * NSEC_PER_MSEC, 0);
    dispatch_source_set_event_handler(timer, ^{
      if (++ticks == 3)
          dispatch_source_cancel(timer);
    });
    dispatch_source_set_cancel_handler(timer, ^{
      dispatch_semaphore_signal(completed);
    });
    dispatch_resume(timer);
    WAIT(completed);
    CHECK(ticks == 3);
    dispatch_release(timer);

    int descriptors[2];
    CHECK(pipe(descriptors) == 0);
    const int input = descriptors[0];
    dispatch_source_t reader =
        dispatch_source_create(DISPATCH_SOURCE_TYPE_READ, descriptors[0], 0, queue);
    CHECK(reader);
    dispatch_source_set_event_handler(reader, ^{
      char text[32];
      CHECK(read(input, text, sizeof(text)) == 8);
      CHECK(!memcmp(text, "event-ok", 8));
      dispatch_source_cancel(reader);
    });
    dispatch_source_set_cancel_handler(reader, ^{
      CHECK(close(input) == 0);
      dispatch_semaphore_signal(completed);
    });
    dispatch_resume(reader);
    CHECK(write(descriptors[1], "event-ok", 8) == 8);
    WAIT(completed);
    CHECK(close(descriptors[1]) == 0);
    dispatch_release(reader);

    CHECK(signal(SIGUSR1, SIG_IGN) != SIG_ERR);
    dispatch_source_t notification =
        dispatch_source_create(DISPATCH_SOURCE_TYPE_SIGNAL, SIGUSR1, 0, queue);
    CHECK(notification);
    dispatch_source_set_registration_handler(notification, ^{
      dispatch_semaphore_signal(completed);
    });
    dispatch_source_set_event_handler(notification, ^{
      CHECK(dispatch_source_get_data(notification) >= 1);
      dispatch_source_cancel(notification);
    });
    dispatch_source_set_cancel_handler(notification, ^{
      dispatch_semaphore_signal(completed);
    });
    dispatch_resume(notification);
    WAIT(completed);
    CHECK(kill(getpid(), SIGUSR1) == 0);
    WAIT(completed);
    dispatch_release(notification);
    dispatch_release(completed);
    dispatch_release(queue);
    puts("dispatch timers, descriptor events and signals passed");
    fflush(stdout);
}
