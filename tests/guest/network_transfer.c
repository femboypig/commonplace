#include <sys/socket.h>
#include <sys/time.h>
#include <netinet/in.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int echo_stream(int client, size_t *total)
{
    char buffer[16384];
    struct timeval timeout = {10, 0};
    if (setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout))
        || setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout))) return -1;
    for (;;) {
        ssize_t count = read(client, buffer, sizeof(buffer));
        if (count < 0 && errno == EINTR) continue;
        if (count < 0) return -1;
        if (!count) return 0;
        *total += (size_t)count;
        for (ssize_t sent = 0; sent < count;) {
            ssize_t written = write(client, buffer + sent, (size_t)(count - sent));
            if (written < 0 && errno == EINTR) continue;
            if (written <= 0) return -1;
            sent += written;
        }
    }
}

int main(void)
{
    int listener = socket(AF_INET, SOCK_STREAM, 0);
    int reuse = 1;
    if (listener < 0 || setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse))) {
        perror("network transfer socket");
        return 1;
    }
    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_len = sizeof(address);
    address.sin_family = AF_INET;
    address.sin_port = htons(7777);
    address.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bind(listener, (struct sockaddr *)&address, sizeof(address)) || listen(listener, 4)) {
        perror("network transfer listen");
        return 1;
    }
    puts("network transfer ready");
    fflush(stdout);
    size_t total = 0;
    for (unsigned connection = 0; connection < 3; ++connection) {
        int client;
        do { client = accept(listener, NULL, NULL); } while (client < 0 && errno == EINTR);
        if (client < 0 || echo_stream(client, &total)) {
            perror("network transfer stream");
            return 1;
        }
        close(client);
    }
    close(listener);
    printf("network transfer passed: connections=3 bytes=%lu\n", (unsigned long)total);
    return 0;
}
