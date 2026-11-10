#include "provider.h"
#include <libkern/crypto/crypto_internal.h>
#include <assert.h>
#include <string.h>

struct digest_vector {
    unsigned algorithm;
    const unsigned char *message;
    size_t size;
    const unsigned char *expected;
};
struct hmac_vector {
    unsigned algorithm;
    const unsigned char *key;
    size_t key_size;
    const unsigned char *message;
    size_t size;
    const unsigned char *expected;
};
#include "digest-vectors.h"

static const struct ccdigest_info *algorithm(unsigned index)
{
    const struct ccdigest_info *digests[] = {
        g_crypto_funcs->ccmd5_di, g_crypto_funcs->ccsha1_di,
        g_crypto_funcs->ccsha256_di, g_crypto_funcs->ccsha384_di,
        g_crypto_funcs->ccsha512_di
    };
    assert(index < sizeof(digests) / sizeof(digests[0]));
    return digests[index];
}

static void check_digests(void)
{
    const size_t chunks[] = {1, 7, 13, 64, 127};
    unsigned char out[64];
    for (size_t v = 0; v < sizeof(digests) / sizeof(digests[0]); ++v) {
        const struct digest_vector *vector = &digests[v];
        const struct ccdigest_info *di = algorithm(vector->algorithm);
        g_crypto_funcs->ccdigest_fn(di, vector->size, vector->message, out);
        assert(!memcmp(out, vector->expected, di->output_size));
        for (size_t c = 0; c < sizeof(chunks) / sizeof(chunks[0]); ++c) {
            ccdigest_di_decl(di, ctx);
            memset(ctx, 0xa5, sizeof(ctx));
            g_crypto_funcs->ccdigest_init_fn(di, ctx);
            for (size_t offset = 0; offset < vector->size;) {
                size_t count = vector->size - offset;
                if (count > chunks[c]) count = chunks[c];
                g_crypto_funcs->ccdigest_update_fn(di, ctx, count, vector->message + offset);
                offset += count;
            }
            g_crypto_funcs->ccdigest_final_fn(di, ctx, out);
            assert(!memcmp(out, vector->expected, di->output_size));
        }
    }
}

static void check_hmacs(void)
{
    unsigned char out[64];
    for (size_t v = 0; v < sizeof(hmacs) / sizeof(hmacs[0]); ++v) {
        const struct hmac_vector *vector = &hmacs[v];
        const struct ccdigest_info *di = algorithm(vector->algorithm);
        g_crypto_funcs->cchmac_fn(di, vector->key_size, vector->key,
            vector->size, vector->message, out);
        assert(!memcmp(out, vector->expected, di->output_size));
        cchmac_di_decl(di, ctx);
        g_crypto_funcs->cchmac_init_fn(di, ctx, vector->key_size, vector->key);
        for (size_t offset = 0; offset < vector->size; ++offset)
            g_crypto_funcs->cchmac_update_fn(di, ctx, 1, vector->message + offset);
        g_crypto_funcs->cchmac_final_fn(di, ctx, out);
        assert(!memcmp(out, vector->expected, di->output_size));
    }
}

int main(void)
{
    commonplace_crypto_init();
    check_digests();
    check_hmacs();
    return 0;
}
