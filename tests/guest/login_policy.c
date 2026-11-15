#include <errno.h>
#include <fcntl.h>
#include <security/pam_appl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/param.h>
#include <unistd.h>

#define CHECK(x)                                                                                   \
    do                                                                                             \
    {                                                                                              \
        if (!(x))                                                                                  \
        {                                                                                          \
            fprintf(stderr, "login policy line %d: %s\n", __LINE__, #x);                           \
            exit(1);                                                                               \
        }                                                                                          \
    } while (0)

static int conversation(int count, const struct pam_message **messages,
                        struct pam_response **result, void *context)
{
    struct pam_response *responses = calloc((size_t)count, sizeof(*responses));
    if (!responses)
        return PAM_BUF_ERR;
    for (int i = 0; i < count; ++i)
    {
        if (messages[i]->msg_style == PAM_PROMPT_ECHO_OFF)
        {
            responses[i].resp = strdup(context);
            if (!responses[i].resp)
            {
                for (int j = 0; j < i; ++j)
                    free(responses[j].resp);
                free(responses);
                return PAM_BUF_ERR;
            }
        }
    }
    *result = responses;
    return PAM_SUCCESS;
}

static void check_account(const char *name, int expected)
{
    struct pam_conv conv = {conversation, "unused"};
    pam_handle_t *handle = NULL;
    CHECK(pam_start("login", name, &conv, &handle) == PAM_SUCCESS);
    int status = pam_acct_mgmt(handle, 0);
    CHECK(status == expected);
    CHECK(pam_end(handle, status) == PAM_SUCCESS);
}

static void check_password(const char *name, const char *password, int accepted)
{
    struct pam_conv conv = {conversation, (void *)password};
    pam_handle_t *handle = NULL;
    CHECK(pam_start("login", name, &conv, &handle) == PAM_SUCCESS);
    int status = pam_authenticate(handle, PAM_DISALLOW_NULL_AUTHTOK);
    CHECK((status == PAM_SUCCESS) == accepted);
    CHECK(pam_end(handle, status) == PAM_SUCCESS);
}

static void check_identity(void)
{
    CHECK(getuid() == 501 && geteuid() == 501);
    CHECK(getgid() == 20 && getegid() == 20);
    gid_t groups[NGROUPS];
    int count = getgroups(NGROUPS, groups);
    CHECK(count > 0);
    int primary = 0;
    for (int i = 0; i < count; ++i)
        primary |= groups[i] == 20;
    CHECK(primary);
    CHECK(setuid(0) == -1 && errno == EPERM);
    CHECK(setgid(0) == -1 && errno == EPERM);
    CHECK(open("/etc/master.passwd", O_RDONLY) == -1 && errno == EACCES);
    CHECK(getuid() == 501 && geteuid() == 501);
    puts("native user credentials: identity, groups and privilege separation passed");
}

static int open_descriptors(void)
{
    int count = 0;
    for (int fd = 0; fd < getdtablesize(); ++fd)
        count += fcntl(fd, F_GETFD) != -1;
    return count;
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--identity") == 0)
    {
        check_identity();
        return 0;
    }
    CHECK(getuid() == 0);
    check_password("tester", "User-check-passphrase-2026!", 1);
    check_password("tester", "User-check-passphrase-2026?", 0);
    check_password("expired", "anything", 0);
    check_password("missing-account", "anything", 0);
    check_account("tester", PAM_SUCCESS);
    check_account("expired", PAM_ACCT_EXPIRED);
    check_account("changed", PAM_NEW_AUTHTOK_REQD);
    int fd = open("/etc/nologin", O_WRONLY | O_CREAT | O_EXCL, 0600);
    CHECK(fd != -1);
    CHECK(write(fd, "maintenance\n", 12) == 12);
    CHECK(close(fd) == 0);
    check_account("tester", PAM_AUTH_ERR);
    check_account("root", PAM_SUCCESS);
    int descriptors = open_descriptors();
    for (unsigned attempt = 0; attempt < 64; ++attempt)
        check_account("tester", PAM_AUTH_ERR);
    CHECK(open_descriptors() == descriptors);
    CHECK(unlink("/etc/nologin") == 0);
    check_account("tester", PAM_SUCCESS);
    puts("native login policy: authentication, locked accounts, expiration and maintenance passed");
    return 0;
}
