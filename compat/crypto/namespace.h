#ifndef COMMONPLACE_CRYPTO_NAMESPACE_H
#define COMMONPLACE_CRYPTO_NAMESPACE_H

/* XNU exports SHA-2 entry points with its own incompatible context ABI. */
#define SHA224_Init cp_openssl_SHA224_Init
#define SHA224_Update cp_openssl_SHA224_Update
#define SHA224_Final cp_openssl_SHA224_Final
#define SHA256_Init cp_openssl_SHA256_Init
#define SHA256_Update cp_openssl_SHA256_Update
#define SHA256_Final cp_openssl_SHA256_Final
#define SHA256_Transform cp_openssl_SHA256_Transform
#define SHA384_Init cp_openssl_SHA384_Init
#define SHA384_Update cp_openssl_SHA384_Update
#define SHA384_Final cp_openssl_SHA384_Final
#define SHA512_Init cp_openssl_SHA512_Init
#define SHA512_Update cp_openssl_SHA512_Update
#define SHA512_Final cp_openssl_SHA512_Final
#define SHA512_Transform cp_openssl_SHA512_Transform

#endif
