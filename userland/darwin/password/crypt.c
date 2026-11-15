/* Native crypt API over the pinned OpenSSL SHA-crypt implementation. */
#include "commonplace_password.h"
#include <dlfcn.h>
#include <errno.h>
#include <openssl/crypto.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>

extern char *commonplace_shacrypt(const char *, const char *, const char *);

static pthread_once_t key_once = PTHREAD_ONCE_INIT;
static pthread_key_t result_key;
static int key_error;
static pthread_mutex_t hash_lock = PTHREAD_MUTEX_INITIALIZER;

static void hash_prepare(void) { pthread_mutex_lock(&hash_lock); }
static void hash_resume(void) { pthread_mutex_unlock(&hash_lock); }

static void create_key(void)
{
    /* pthread_atfork callbacks must remain mapped after a PAM module unload. */
    if (!dlopen("/usr/lib/libcrypt.dylib", RTLD_NOW | RTLD_NODELETE))
    {
        key_error = ENOEXEC;
        return;
    }
    key_error = pthread_key_create(&result_key, free);
    if (!key_error)
        key_error = pthread_atfork(hash_prepare, hash_resume, hash_resume);
}

static int normalize_setting(const char *setting, char *salt, size_t size)
{
    if (!setting || strncmp(setting, "$6$", 3) != 0)
        return EINVAL;
    const char *begin = setting + 3;
    const char *value = begin;
    if (strncmp(value, "rounds=", 7) == 0)
    {
        value += 7;
        const char *digit = value;
        unsigned rounds = 0;
        while (*value >= '0' && *value <= '9')
        {
            if (rounds > 1000000 / 10)
                return EINVAL;
            rounds = rounds * 10 + (unsigned)(*value++ - '0');
        }
        if (value == digit || *value++ != '$' || rounds < 1000 || rounds > 1000000)
            return EINVAL;
    }
    const char *salt_begin = value;
    while (*value && *value != '$')
    {
        unsigned char c = (unsigned char)*value++;
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
              c == '.' || c == '/'))
            return EINVAL;
    }
    if (value == salt_begin || value - salt_begin > 16 || (size_t)(value - begin) >= size)
        return EINVAL;
    memcpy(salt, begin, (size_t)(value - begin));
    salt[value - begin] = 0;
    return 0;
}

char *crypt(const char *password, const char *setting)
{
    char salt[64];
    int error = normalize_setting(setting, salt, sizeof(salt));
    if (!error && (!password || strnlen(password, 1025) > 1024))
        error = EINVAL;
    if (!error)
        error = pthread_once(&key_once, create_key);
    if (!error)
        error = key_error;
    if (error)
    {
        errno = error;
        return NULL;
    }
    char *result = pthread_getspecific(result_key);
    if (!result)
    {
        result = calloc(1, 128);
        if (!result)
            return NULL;
        error = pthread_setspecific(result_key, result);
        if (error)
        {
            free(result);
            errno = error;
            return NULL;
        }
    }
    error = pthread_mutex_lock(&hash_lock);
    if (error)
    {
        errno = error;
        return NULL;
    }
    const char *hash = commonplace_shacrypt(password, "6", salt);
    if (hash)
        strlcpy(result, hash, 128);
    pthread_mutex_unlock(&hash_lock);
    if (!hash)
    {
        errno = ENOMEM;
        return NULL;
    }
    return result;
}

int commonplace_password_verify(const char *password, const char *stored)
{
    char *actual = crypt(password, stored);
    return actual && strlen(actual) == strlen(stored) &&
           CRYPTO_memcmp(actual, stored, strlen(stored)) == 0;
}
