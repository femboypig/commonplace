#include "provider.h"
#include <libkern/crypto/crypto_internal.h>
#include <assert.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

enum { AES_ECB, AES_CBC, AES_GCM, AES_XTS, DES_ECB, DES_CBC,
       DES3_ECB, DES3_CBC, BLOWFISH_ECB, CAST_ECB, RC4_STREAM };

struct cipher_vector {
    unsigned mode;
    const unsigned char *key;
    size_t key_size;
    const unsigned char *iv;
    size_t iv_size;
    const unsigned char *aad;
    size_t aad_size;
    const unsigned char *plain, *cipher;
    size_t size;
    const unsigned char *tag;
    size_t tag_size;
};
#include "cipher-vectors.h"

static void *context(size_t size)
{
    unsigned char *buffer = malloc(size + 32);
    assert(buffer);
    memset(buffer, 0xa5, size + 32);
    return buffer + 16;
}

static void release(void *ctx, size_t size)
{
    unsigned char *buffer = ctx;
    for (unsigned i = 0; i < 16; ++i)
        assert(buffer[(ptrdiff_t)i - 16] == 0xa5 && buffer[size + i] == 0xa5);
    free(buffer - 16);
}

static void ecb(const struct cipher_vector *v, const struct ccmode_ecb *mode, int decrypt)
{
    ccecb_ctx *ctx = context(mode->size);
    unsigned char *buffer = context(v->size);
    mode->init(mode, ctx, v->key_size, v->key);
    memcpy(buffer, decrypt ? v->cipher : v->plain, v->size);
    mode->ecb(ctx, v->size / mode->block_size, buffer, buffer);
    assert(!memcmp(buffer, decrypt ? v->plain : v->cipher, v->size));
    release(buffer, v->size);
    release(ctx, mode->size);
}

static void cbc(const struct cipher_vector *v, const struct ccmode_cbc *mode, int decrypt)
{
    cccbc_ctx *ctx = context(mode->size);
    unsigned char *buffer = context(v->size);
    cccbc_iv_decl(mode->block_size, iv);
    mode->init(mode, ctx, v->key_size, v->key);
    cccbc_set_iv(mode, iv, v->iv);
    memcpy(buffer, decrypt ? v->cipher : v->plain, v->size);
    mode->cbc(ctx, iv, 0, NULL, NULL);
    assert(!memcmp(iv, v->iv, mode->block_size));
    for (size_t offset = 0; offset < v->size; offset += mode->block_size)
        mode->cbc(ctx, iv, 1, buffer + offset, buffer + offset);
    assert(!memcmp(buffer, decrypt ? v->plain : v->cipher, v->size));
    assert(!memcmp(iv, v->cipher + v->size - mode->block_size, mode->block_size));
    release(buffer, v->size);
    release(ctx, mode->size);
}

static void gcm(const struct cipher_vector *v, const struct ccmode_gcm *mode, int decrypt)
{
    ccgcm_ctx *ctx = context(mode->size);
    unsigned char *buffer = context(v->size), tag[16];
    mode->init(mode, ctx, v->key_size, v->key);
    for (unsigned repeat = 0; repeat < 2; ++repeat) {
        mode->set_iv(ctx, v->iv_size, v->iv);
        mode->gmac(ctx, v->aad_size, v->aad);
        /* Verify copied contexts repair the backend's internal key pointer. */
        ccgcm_ctx *copy = context(mode->size);
        memcpy(copy, ctx, mode->size);
        release(ctx, mode->size);
        ctx = copy;
        memcpy(buffer, decrypt ? v->cipher : v->plain, v->size);
        for (size_t offset = 0; offset < v->size;) {
            size_t size = v->size - offset;
            if (size > 7) size = 7;
            mode->gcm(ctx, size, buffer + offset, buffer + offset);
            offset += size;
        }
        mode->finalize(ctx, v->tag_size, tag);
        assert(!memcmp(buffer, decrypt ? v->plain : v->cipher, v->size));
        assert(!memcmp(tag, v->tag, v->tag_size));
        mode->reset(ctx);
    }
    release(buffer, v->size);
    release(ctx, mode->size);
}

static void xts(const struct cipher_vector *v, const struct ccmode_xts *mode, int decrypt)
{
    ccxts_ctx *ctx = context(mode->size);
    unsigned char *buffer = context(v->size);
    ccxts_tweak_decl(mode->tweak_size, tweak);
    mode->init(mode, ctx, v->key_size / 2, v->key, v->key + v->key_size / 2);
    mode->set_tweak(ctx, tweak, v->iv);
    memcpy(buffer, decrypt ? v->cipher : v->plain, v->size);
    for (size_t offset = 0; offset < v->size; offset += 16)
        assert(mode->xts(ctx, tweak, 1, buffer + offset, buffer + offset) == tweak);
    assert(!memcmp(buffer, decrypt ? v->plain : v->cipher, v->size));
    release(buffer, v->size);
    release(ctx, mode->size);
}

static void check_vector(const struct cipher_vector *v)
{
    for (int decrypt = 0; decrypt < 2; ++decrypt) {
        switch (v->mode) {
        case AES_ECB: ecb(v, decrypt ? &cp_aes_ecb_dec : &cp_aes_ecb_enc, decrypt); break;
        case AES_CBC: cbc(v, decrypt ? &cp_aes_cbc_dec : &cp_aes_cbc_enc, decrypt); break;
        case AES_GCM: gcm(v, decrypt ? &cp_aes_gcm_dec : &cp_aes_gcm_enc, decrypt); break;
        case AES_XTS: xts(v, decrypt ? &cp_aes_xts_dec : &cp_aes_xts_enc, decrypt); break;
        case DES_ECB: ecb(v, decrypt ? &cp_des_ecb_dec : &cp_des_ecb_enc, decrypt); break;
        case DES_CBC: cbc(v, decrypt ? &cp_des_cbc_dec : &cp_des_cbc_enc, decrypt); break;
        case DES3_ECB: ecb(v, decrypt ? &cp_des3_ecb_dec : &cp_des3_ecb_enc, decrypt); break;
        case DES3_CBC: cbc(v, decrypt ? &cp_des3_cbc_dec : &cp_des3_cbc_enc, decrypt); break;
        case BLOWFISH_ECB: ecb(v, decrypt ? &cp_blowfish_ecb_dec : &cp_blowfish_ecb_enc, decrypt); break;
        case CAST_ECB: ecb(v, decrypt ? &cp_cast_ecb_dec : &cp_cast_ecb_enc, decrypt); break;
        case RC4_STREAM: {
            ccrc4_ctx *ctx = context(cp_rc4.size);
            unsigned char *buffer = context(v->size);
            cp_rc4.init(ctx, v->key_size, v->key);
            memcpy(buffer, decrypt ? v->cipher : v->plain, v->size);
            for (size_t i = 0; i < v->size; ++i)
                cp_rc4.crypt(ctx, 1, buffer + i, buffer + i);
            assert(!memcmp(buffer, decrypt ? v->plain : v->cipher, v->size));
            release(buffer, v->size);
            release(ctx, cp_rc4.size);
            break;
        }
        default: assert(0);
        }
    }
}

int main(void)
{
    commonplace_crypto_init();
    for (size_t i = 0; i < sizeof(ciphers) / sizeof(ciphers[0]); ++i)
        check_vector(&ciphers[i]);
    unsigned char weak[8] = {1, 1, 1, 1, 1, 1, 1, 1};
    assert(cp_des_is_weak(weak, sizeof(weak)));
    memset(weak, 0, sizeof(weak));
    cp_des_set_parity(weak, sizeof(weak));
    for (size_t i = 0; i < sizeof(weak); ++i) assert(weak[i] == 1);
    return 0;
}
