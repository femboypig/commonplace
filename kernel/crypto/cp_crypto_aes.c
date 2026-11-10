#include "provider.h"
#include <openssl/aes.h>

static void aes_init_enc(const struct ccmode_ecb *mode __attribute__((unused)),
    ccecb_ctx *ctx, size_t length, const void *key)
{
    if ((length != 16 && length != 24 && length != 32) ||
        AES_set_encrypt_key(key, (int)length * 8, (void *)ctx) != 0)
        cp_crypto_fail("invalid AES encryption key");
}

static void aes_init_dec(const struct ccmode_ecb *mode __attribute__((unused)),
    ccecb_ctx *ctx, size_t length, const void *key)
{
    if ((length != 16 && length != 24 && length != 32) ||
        AES_set_decrypt_key(key, (int)length * 8, (void *)ctx) != 0)
        cp_crypto_fail("invalid AES decryption key");
}

static void aes_enc(const ccecb_ctx *ctx, unsigned long blocks,
    const void *input, void *output)
{
    const unsigned char *in = input;
    unsigned char *out = output;
    while (blocks--) {
        AES_encrypt(in, out, (const void *)ctx);
        in += 16;
        out += 16;
    }
}

static void aes_dec(const ccecb_ctx *ctx, unsigned long blocks,
    const void *input, void *output)
{
    const unsigned char *in = input;
    unsigned char *out = output;
    while (blocks--) {
        AES_decrypt(in, out, (const void *)ctx);
        in += 16;
        out += 16;
    }
}

const struct ccmode_ecb cp_aes_ecb_enc = {sizeof(AES_KEY), 16, aes_init_enc, aes_enc};
const struct ccmode_ecb cp_aes_ecb_dec = {sizeof(AES_KEY), 16, aes_init_dec, aes_dec};
const struct ccmode_cbc cp_aes_cbc_enc = CP_CBC_MODE(AES_KEY, 16, cp_aes_ecb_enc, cp_cbc_encrypt);
const struct ccmode_cbc cp_aes_cbc_dec = CP_CBC_MODE(AES_KEY, 16, cp_aes_ecb_dec, cp_cbc_decrypt);
