#include "dispatch_checks.h"
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

void check_dispatch_io(void)
{
    static unsigned char payload[257 * 1024];
    for (size_t i = 0; i < sizeof(payload); ++i)
        payload[i] = (unsigned char)(i * 17 + i / 257);
    dispatch_queue_t queue = dispatch_queue_create("commonplace.io", NULL);
    dispatch_semaphore_t completed = dispatch_semaphore_create(0);
    CHECK(queue && completed);
    dispatch_io_t channel =
        dispatch_io_create_with_path(DISPATCH_IO_RANDOM, "/tmp/dispatch-data",
                                     O_CREAT | O_TRUNC | O_RDWR, 0600, queue, ^(int error) {
                                       CHECK(!error);
                                       dispatch_semaphore_signal(completed);
                                     });
    CHECK(channel);
    dispatch_data_t data =
        dispatch_data_create(payload, sizeof(payload), queue, DISPATCH_DATA_DESTRUCTOR_DEFAULT);
    CHECK(data);
    dispatch_io_write(channel, 0, data, queue, ^(bool done, dispatch_data_t remaining, int error) {
      (void)remaining;
      CHECK(!error);
      if (done)
          dispatch_semaphore_signal(completed);
    });
    WAIT(completed);
    dispatch_release(data);
    __block size_t received = 0;
    dispatch_io_read(
        channel, 0, sizeof(payload), queue, ^(bool done, dispatch_data_t chunk, int error) {
          CHECK(!error);
          if (chunk)
              CHECK(dispatch_data_apply(chunk, ^bool(dispatch_data_t region, size_t offset,
                                                     const void *buffer, size_t size) {
                (void)region;
                CHECK(received + offset + size <= sizeof(payload));
                CHECK(!memcmp(buffer, payload + received + offset, size));
                return true;
              }));
          received += chunk ? dispatch_data_get_size(chunk) : 0;
          if (done)
              dispatch_semaphore_signal(completed);
        });
    WAIT(completed);
    CHECK(received == sizeof(payload));
    dispatch_io_close(channel, 0);
    WAIT(completed);
    dispatch_release(channel);
    CHECK(unlink("/tmp/dispatch-data") == 0);
    dispatch_release(completed);
    dispatch_release(queue);
    puts("dispatch asynchronous file IO passed");
    fflush(stdout);
}
