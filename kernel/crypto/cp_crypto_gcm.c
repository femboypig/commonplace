#include "provider.h"
#include <openssl/aes.h>
#include <crypto/modes.h>

struct gcm_key { AES_KEY aes; GCM128_CONTEXT state; };

static void aes_block(const unsigned char in[16], unsigned char out[16], const void *key)
{
    AES_encrypt(in, out, key);
}

static void gcm_init(const struct ccmode_gcm *mode __attribute__((unused)),
    ccgcm_ctx *opaque, size_t length, const void *key)
{
    struct gcm_key *ctx = (void *)opaque;
    if ((length != 16 && length != 24 && length != 32) ||
        AES_set_encrypt_key(key, (int)length * 8, &ctx->aes) != 0)
        cp_crypto_fail("invalid AES-GCM key length");
    CRYPTO_gcm128_init(&ctx->state, &ctx->aes, aes_block);
}

static struct gcm_key *gcm_context(ccgcm_ctx *opaque)
{
    struct gcm_key *ctx = (void *)opaque;
    /* Keep contexts relocatable even though OpenSSL retains a key pointer. */
    ctx->state.key = &ctx->aes;
    return ctx;
}

static void gcm_iv(ccgcm_ctx *opaque, size_t size, const void *iv)
{
    struct gcm_key *ctx = gcm_context(opaque);
    CRYPTO_gcm128_setiv(&ctx->state, iv, size);
}

static void gcm_aad(ccgcm_ctx *opaque, size_t size, const void *data)
{
    struct gcm_key *ctx = gcm_context(opaque);
    if (CRYPTO_gcm128_aad(&ctx->state, data, size) != 0)
        cp_crypto_fail("invalid AES-GCM authenticated-data state");
}

static void gcm_encrypt(ccgcm_ctx *opaque, size_t size, const void *in, void *out)
{
    struct gcm_key *ctx = gcm_context(opaque);
    if (CRYPTO_gcm128_encrypt(&ctx->state, in, out, size) != 0)
        cp_crypto_fail("invalid AES-GCM encryption state");
}

static void gcm_decrypt(ccgcm_ctx *opaque, size_t size, const void *in, void *out)
{
    struct gcm_key *ctx = gcm_context(opaque);
    if (CRYPTO_gcm128_decrypt(&ctx->state, in, out, size) != 0)
        cp_crypto_fail("invalid AES-GCM decryption state");
}

static void gcm_final(ccgcm_ctx *opaque, size_t size, void *tag)
{
    struct gcm_key *ctx = gcm_context(opaque);
    if (size > 16)
        cp_crypto_fail("invalid AES-GCM tag size");
    CRYPTO_gcm128_tag(&ctx->state, tag, size);
}

static void gcm_reset(ccgcm_ctx *opaque)
{
    struct gcm_key *ctx = gcm_context(opaque);
    CRYPTO_gcm128_init(&ctx->state, &ctx->aes, aes_block);
}

const struct ccmode_gcm cp_aes_gcm_enc = {
    sizeof(struct gcm_key), 1, gcm_init, gcm_iv, gcm_aad, gcm_encrypt, gcm_final, gcm_reset, NULL};
const struct ccmode_gcm cp_aes_gcm_dec = {
    sizeof(struct gcm_key), 1, gcm_init, gcm_iv, gcm_aad, gcm_decrypt, gcm_final, gcm_reset, NULL};
