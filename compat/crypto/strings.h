#ifndef COMMONPLACE_CRYPTO_STRINGS_H
#define COMMONPLACE_CRYPTO_STRINGS_H
#include <stddef.h>
int bcmp(const void *, const void *, size_t);
void bcopy(const void *, void *, size_t);
void bzero(void *, size_t);
int strcasecmp(const char *, const char *);
int strncasecmp(const char *, const char *, size_t);
#endif
