#include "provider.h"
#include <openssl/blowfish.h>
#include <openssl/cast.h>
#include <openssl/rc4.h>

static void blowfish_init(const struct ccmode_ecb *mode __attribute__((unused)),
    ccecb_ctx *ctx, size_t length, const void *key)
{
    if (!length || length > 56)
        cp_crypto_fail("invalid Blowfish key length");
    BF_set_key((void *)ctx, (int)length, key);
}

static void cast_init(const struct ccmode_ecb *mode __attribute__((unused)),
    ccecb_ctx *ctx, size_t length, const void *key)
{
    if (length < 5 || length > 16)
        cp_crypto_fail("invalid CAST key length");
    CAST_set_key((void *)ctx, (int)length, key);
}

#define ECB_BLOCKS(name, function, direction) \
    static void name(const ccecb_ctx *ctx, unsigned long blocks, const void *input, void *output) \
    { \
        const unsigned char *in = input; \
        unsigned char *out = output; \
        while (blocks--) { function(in, out, (const void *)ctx, direction); in += 8; out += 8; } \
    }
ECB_BLOCKS(blowfish_enc, BF_ecb_encrypt, BF_ENCRYPT)
ECB_BLOCKS(blowfish_dec, BF_ecb_encrypt, BF_DECRYPT)
ECB_BLOCKS(cast_enc, CAST_ecb_encrypt, CAST_ENCRYPT)
ECB_BLOCKS(cast_dec, CAST_ecb_encrypt, CAST_DECRYPT)

const struct ccmode_ecb cp_blowfish_ecb_enc = {sizeof(BF_KEY), 8, blowfish_init, blowfish_enc};
const struct ccmode_ecb cp_blowfish_ecb_dec = {sizeof(BF_KEY), 8, blowfish_init, blowfish_dec};
const struct ccmode_ecb cp_cast_ecb_enc = {sizeof(CAST_KEY), 8, cast_init, cast_enc};
const struct ccmode_ecb cp_cast_ecb_dec = {sizeof(CAST_KEY), 8, cast_init, cast_dec};

static void rc4_init(ccrc4_ctx *ctx, size_t length, const void *key)
{
    if (!length || length > 256)
        cp_crypto_fail("invalid RC4 key length");
    RC4_set_key((void *)ctx, (int)length, key);
}

static void rc4_crypt(ccrc4_ctx *ctx, unsigned long length, const void *in, void *out)
{
    RC4((void *)ctx, length, in, out);
}

const struct ccrc4_info cp_rc4 = {sizeof(RC4_KEY), rc4_init, rc4_crypt};
