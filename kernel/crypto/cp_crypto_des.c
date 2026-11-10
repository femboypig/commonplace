#include "provider.h"
#include <openssl/des.h>

struct des3_key { DES_key_schedule keys[3]; };

static void des_init(const struct ccmode_ecb *mode, ccecb_ctx *ctx,
    size_t length, const void *key)
{
    unsigned count = mode->size == sizeof(DES_key_schedule) ? 1 : 3;
    if ((count == 1 && length != 8) || (count == 3 && length != 16 && length != 24))
        cp_crypto_fail("invalid DES key length");
    DES_key_schedule *keys = (void *)ctx;
    const unsigned char *bytes = key;
    for (unsigned i = 0; i < count; ++i) {
        size_t offset = i == 2 && length == 16 ? 0 : i * 8;
        DES_set_key_unchecked((const_DES_cblock *)(bytes + offset), &keys[i]);
    }
}

static void des_blocks(const ccecb_ctx *ctx, unsigned long blocks,
    const void *input, void *output, int encrypt, int triple)
{
    /* OpenSSL's legacy DES API takes mutable schedules but never changes them. */
    DES_key_schedule *keys = (DES_key_schedule *)(void *)ctx;
    const unsigned char *in = input;
    unsigned char *out = output;
    while (blocks--) {
        if (triple)
            DES_ecb3_encrypt((const_DES_cblock *)in, (DES_cblock *)out,
                &keys[0], &keys[1], &keys[2], encrypt);
        else
            DES_ecb_encrypt((const_DES_cblock *)in, (DES_cblock *)out, keys, encrypt);
        in += 8;
        out += 8;
    }
}

#define DES_BLOCKS(name, direction, triple) \
    static void name(const ccecb_ctx *ctx, unsigned long blocks, const void *in, void *out) \
    { des_blocks(ctx, blocks, in, out, direction, triple); }
DES_BLOCKS(des_enc, DES_ENCRYPT, 0)
DES_BLOCKS(des_dec, DES_DECRYPT, 0)
DES_BLOCKS(des3_enc, DES_ENCRYPT, 1)
DES_BLOCKS(des3_dec, DES_DECRYPT, 1)

const struct ccmode_ecb cp_des_ecb_enc = {sizeof(DES_key_schedule), 8, des_init, des_enc};
const struct ccmode_ecb cp_des_ecb_dec = {sizeof(DES_key_schedule), 8, des_init, des_dec};
const struct ccmode_ecb cp_des3_ecb_enc = {sizeof(struct des3_key), 8, des_init, des3_enc};
const struct ccmode_ecb cp_des3_ecb_dec = {sizeof(struct des3_key), 8, des_init, des3_dec};
const struct ccmode_cbc cp_des_cbc_enc = {
    sizeof(struct cp_cbc_context) + sizeof(DES_key_schedule), 8,
    cp_cbc_init, cp_cbc_encrypt, &cp_des_ecb_enc};
const struct ccmode_cbc cp_des_cbc_dec = {
    sizeof(struct cp_cbc_context) + sizeof(DES_key_schedule), 8,
    cp_cbc_init, cp_cbc_decrypt, &cp_des_ecb_dec};
const struct ccmode_cbc cp_des3_cbc_enc = {
    sizeof(struct cp_cbc_context) + sizeof(struct des3_key), 8,
    cp_cbc_init, cp_cbc_encrypt, &cp_des3_ecb_enc};
const struct ccmode_cbc cp_des3_cbc_dec = {
    sizeof(struct cp_cbc_context) + sizeof(struct des3_key), 8,
    cp_cbc_init, cp_cbc_decrypt, &cp_des3_ecb_dec};

int cp_des_is_weak(void *key, unsigned long length)
{
    unsigned char *bytes = key;
    if (!length || length % 8)
        return 1;
    for (unsigned long offset = 0; offset < length; offset += 8)
        if (DES_is_weak_key((const_DES_cblock *)(bytes + offset)))
            return 1;
    return 0;
}

void cp_des_set_parity(void *key, unsigned long length)
{
    unsigned char *bytes = key;
    if (length % 8)
        cp_crypto_fail("invalid DES parity buffer");
    for (unsigned long offset = 0; offset < length; offset += 8)
        DES_set_odd_parity((DES_cblock *)(bytes + offset));
}
