#include "commonplace_password.h"
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define CHECK(x)                                                                                   \
    do                                                                                             \
    {                                                                                              \
        if (!(x))                                                                                  \
        {                                                                                          \
            fprintf(stderr, "password check line %d: %s\n", __LINE__, #x);                         \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)

/* OpenSSL's published SHA-crypt known-answer test. */
static const char *expected = "$6$saltstring$svn8UoSVapNtMuq1ukKS4tPQd8iKwSMHWjl/"
                              "O817G3uBnIFNjnQJuesI68u4OTLiBFdcbYEdFCoEOfaS35inz1";

static void *worker(void *unused)
{
    (void)unused;
    for (unsigned i = 0; i < 4; ++i)
    {
        char *hash = crypt("Hello world!", "$6$saltstring");
        CHECK(hash && strcmp(hash, expected) == 0);
        CHECK(commonplace_password_verify("Hello world!", expected));
        CHECK(!commonplace_password_verify("Hello world?", expected));
    }
    return NULL;
}

int main(void)
{
    worker(NULL);
    CHECK(!crypt("test", "ab"));
    CHECK(!crypt("test", "$6$rounds=999999999999$salt"));
    CHECK(!crypt("test", "$6$rounds=0$salt"));
    CHECK(!crypt("test", "$6$"));
    CHECK(!crypt("test", "$6$invalid salt"));
    CHECK(!commonplace_password_verify("test", "*"));
    CHECK(!commonplace_password_verify(NULL, expected));
    pthread_t threads[4];
    for (unsigned i = 0; i < 4; ++i)
        CHECK(pthread_create(&threads[i], NULL, worker, NULL) == 0);
    for (unsigned i = 0; i < 4; ++i)
        CHECK(pthread_join(threads[i], NULL) == 0);
    pid_t child = fork();
    CHECK(child >= 0);
    if (!child)
    {
        worker(NULL);
        _exit(0);
    }
    int status;
    CHECK(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 0);
    puts(
        "native password hashing: known vectors, full passwords, thread isolation and fork passed");
    return 0;
}
