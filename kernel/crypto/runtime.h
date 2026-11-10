#ifndef COMMONPLACE_CRYPTO_RUNTIME_H
#define COMMONPLACE_CRYPTO_RUNTIME_H
#include <stddef.h>
void OPENSSL_die(const char *, const char *, int) __attribute__((noreturn));
void OPENSSL_cleanse(void *, size_t);
int CRYPTO_memcmp(const void *, const void *, size_t);
size_t OPENSSL_strlcpy(char *, const char *, size_t);
void *CRYPTO_malloc(size_t, const char *, int);
void CRYPTO_free(void *, const char *, int);
void CRYPTO_clear_free(void *, size_t, const char *, int);
#endif
