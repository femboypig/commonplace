#ifndef COMMONPLACE_CRYPTO_PROVIDER_H
#define COMMONPLACE_CRYPTO_PROVIDER_H

#include <libkern/crypto/register_crypto.h>

void commonplace_crypto_init(void);
void cp_crypto_fail(const char *reason) __attribute__((noreturn));
void cp_digest_prepare(void);
void cp_crypto_selftest(void);

extern const struct ccdigest_info cp_md5, cp_sha256, cp_sha384, cp_sha512;
extern const struct ccmode_ecb cp_aes_ecb_enc, cp_aes_ecb_dec;
extern const struct ccmode_ecb cp_des_ecb_enc, cp_des_ecb_dec;
extern const struct ccmode_ecb cp_des3_ecb_enc, cp_des3_ecb_dec;
extern const struct ccmode_ecb cp_blowfish_ecb_enc, cp_blowfish_ecb_dec;
extern const struct ccmode_ecb cp_cast_ecb_enc, cp_cast_ecb_dec;
extern const struct ccmode_cbc cp_aes_cbc_enc, cp_aes_cbc_dec;
extern const struct ccmode_cbc cp_des_cbc_enc, cp_des_cbc_dec;
extern const struct ccmode_cbc cp_des3_cbc_enc, cp_des3_cbc_dec;
extern const struct ccmode_xts cp_aes_xts_enc, cp_aes_xts_dec;
extern const struct ccmode_gcm cp_aes_gcm_enc, cp_aes_gcm_dec;
extern const struct ccrc4_info cp_rc4;

int cp_des_is_weak(void *key, unsigned long length);
void cp_des_set_parity(void *key, unsigned long length);

/* CBC stores a descriptor pointer followed by an aligned ECB key schedule. */
struct cp_cbc_context {
    const struct ccmode_ecb *ecb;
    unsigned char key[] __attribute__((aligned(16)));
};

void cp_cbc_init(const struct ccmode_cbc *, cccbc_ctx *, size_t, const void *);
void cp_cbc_encrypt(const cccbc_ctx *, cccbc_iv *, unsigned long, const void *, void *);
void cp_cbc_decrypt(const cccbc_ctx *, cccbc_iv *, unsigned long, const void *, void *);

#define CP_CBC_MODE(key_type, block_size, ecb_mode, operation) \
    { sizeof(struct cp_cbc_context) + sizeof(key_type), block_size, \
      cp_cbc_init, operation, &ecb_mode }

#endif
