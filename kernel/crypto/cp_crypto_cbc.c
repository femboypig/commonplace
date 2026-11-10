#include "provider.h"
#include <string.h>

void cp_cbc_init(const struct ccmode_cbc *mode, cccbc_ctx *opaque,
    size_t length, const void *key)
{
    struct cp_cbc_context *ctx = (void *)opaque;
    ctx->ecb = mode->custom;
    if (!ctx->ecb || !ctx->ecb->block_size || ctx->ecb->block_size > 16 ||
        mode->size < sizeof(*ctx) + ctx->ecb->size)
        cp_crypto_fail("invalid CBC descriptor");
    ctx->ecb->init(ctx->ecb, (void *)ctx->key, length, key);
}

void cp_cbc_encrypt(const cccbc_ctx *opaque, cccbc_iv *iv,
    unsigned long blocks, const void *input, void *output)
{
    const struct cp_cbc_context *ctx = (const void *)opaque;
    const unsigned char *in = input;
    unsigned char *out = output, *chain = (void *)iv;
    size_t size = ctx->ecb->block_size;
    unsigned char block[16];
    while (blocks--) {
        for (size_t i = 0; i < size; ++i)
            block[i] = in[i] ^ chain[i];
        ctx->ecb->ecb((const void *)ctx->key, 1, block, out);
        memcpy(chain, out, size);
        in += size;
        out += size;
    }
    cc_clear(sizeof(block), block);
}

void cp_cbc_decrypt(const cccbc_ctx *opaque, cccbc_iv *iv,
    unsigned long blocks, const void *input, void *output)
{
    const struct cp_cbc_context *ctx = (const void *)opaque;
    const unsigned char *in = input;
    unsigned char *out = output, *chain = (void *)iv;
    size_t size = ctx->ecb->block_size;
    unsigned char block[16], saved[16];
    while (blocks--) {
        memcpy(saved, in, size);
        ctx->ecb->ecb((const void *)ctx->key, 1, in, block);
        for (size_t i = 0; i < size; ++i)
            out[i] = block[i] ^ chain[i];
        memcpy(chain, saved, size);
        in += size;
        out += size;
    }
    cc_clear(sizeof(block), block);
    cc_clear(sizeof(saved), saved);
}
