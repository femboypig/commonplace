#include "provider.h"
#include <openssl/aes.h>
#include <string.h>

struct xts_key {
    AES_KEY data __attribute__((aligned(16)));
    AES_KEY tweak __attribute__((aligned(16)));
};

static void xts_init(const struct ccmode_xts *mode, ccxts_ctx *opaque,
    size_t length, const void *key, const void *tweak_key)
{
    struct xts_key *ctx = (void *)opaque;
    if (length != 16 && length != 32)
        cp_crypto_fail("invalid AES-XTS key length");
    const struct ccmode_ecb *data_mode = mode->custom;
    const struct ccmode_ecb *tweak_mode = mode->custom1;
    data_mode->init(data_mode, (void *)&ctx->data, length, key);
    tweak_mode->init(tweak_mode, (void *)&ctx->tweak, length, tweak_key);
}

static void xts_tweak(const ccxts_ctx *opaque, ccxts_tweak *tweak, const void *iv)
{
    const struct xts_key *ctx = (const void *)opaque;
    AES_encrypt(iv, (void *)tweak, &ctx->tweak);
}

static void next_tweak(unsigned char tweak[16])
{
    unsigned carry = 0;
    for (unsigned i = 0; i < 16; ++i) {
        unsigned next = tweak[i] >> 7;
        tweak[i] = (tweak[i] << 1) | carry;
        carry = next;
    }
    tweak[0] ^= 0x87 & -carry;
}

static void *xts_blocks(const ccxts_ctx *opaque, ccxts_tweak *tweak,
    unsigned long blocks, const void *input, void *output, int decrypt)
{
    const struct xts_key *ctx = (const void *)opaque;
    const unsigned char *in = input;
    unsigned char *out = output, *chain = (void *)tweak;
    unsigned char block[16];
    while (blocks--) {
        for (unsigned i = 0; i < 16; ++i)
            block[i] = in[i] ^ chain[i];
        if (decrypt)
            AES_decrypt(block, block, &ctx->data);
        else
            AES_encrypt(block, block, &ctx->data);
        for (unsigned i = 0; i < 16; ++i)
            out[i] = block[i] ^ chain[i];
        next_tweak(chain);
        in += 16;
        out += 16;
    }
    cc_clear(sizeof(block), block);
    return tweak;
}

static void *xts_enc(const ccxts_ctx *ctx, ccxts_tweak *tweak,
    unsigned long blocks, const void *in, void *out)
{
    return xts_blocks(ctx, tweak, blocks, in, out, 0);
}

static void *xts_dec(const ccxts_ctx *ctx, ccxts_tweak *tweak,
    unsigned long blocks, const void *in, void *out)
{
    return xts_blocks(ctx, tweak, blocks, in, out, 1);
}

const struct ccmode_xts cp_aes_xts_enc = {
    sizeof(struct xts_key), 16, 16, xts_init, xts_tweak, xts_enc,
    &cp_aes_ecb_enc, &cp_aes_ecb_enc};
const struct ccmode_xts cp_aes_xts_dec = {
    sizeof(struct xts_key), 16, 16, xts_init, xts_tweak, xts_dec,
    &cp_aes_ecb_dec, &cp_aes_ecb_enc};
