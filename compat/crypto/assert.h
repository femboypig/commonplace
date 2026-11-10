#ifndef COMMONPLACE_CRYPTO_ASSERT_H
#define COMMONPLACE_CRYPTO_ASSERT_H
void OPENSSL_die(const char *, const char *, int) __attribute__((noreturn));
#define assert(condition) ((condition) ? (void)0 : OPENSSL_die(#condition, __FILE__, __LINE__))
#endif
