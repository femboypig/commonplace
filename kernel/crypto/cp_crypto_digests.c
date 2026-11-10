#include "provider.h"
#include <corecrypto/ccdigest_priv.h>
#include <corecrypto/ccmd5.h>
#include <corecrypto/ccsha2.h>
#include <openssl/md5.h>
#include <openssl/sha.h>
#include <string.h>

static uint32_t md5_initial[4], sha256_initial[8];
static uint64_t sha384_initial[8], sha512_initial[8];

void cp_digest_prepare(void)
{
    MD5_CTX md5;
    SHA256_CTX sha256;
    SHA512_CTX sha512;
    MD5_Init(&md5);
    memcpy(md5_initial, &md5.A, sizeof(md5_initial));
    SHA256_Init(&sha256);
    memcpy(sha256_initial, sha256.h, sizeof(sha256_initial));
    SHA384_Init(&sha512);
    memcpy(sha384_initial, sha512.h, sizeof(sha384_initial));
    SHA512_Init(&sha512);
    memcpy(sha512_initial, sha512.h, sizeof(sha512_initial));
    cc_clear(sizeof(md5), &md5);
    cc_clear(sizeof(sha256), &sha256);
    cc_clear(sizeof(sha512), &sha512);
}

static void md5_compress(ccdigest_state_t state, unsigned long blocks, const void *data)
{
    MD5_CTX hash = {0};
    const unsigned char *input = data;
    memcpy(&hash.A, ccdigest_u8(state), sizeof(md5_initial));
    while (blocks--) {
        MD5_Transform(&hash, input);
        input += 64;
    }
    memcpy(ccdigest_u8(state), &hash.A, sizeof(md5_initial));
    cc_clear(sizeof(hash), &hash);
}

static void sha256_compress(ccdigest_state_t state, unsigned long blocks, const void *data)
{
    SHA256_CTX hash = {0};
    const unsigned char *input = data;
    memcpy(hash.h, ccdigest_u8(state), sizeof(sha256_initial));
    while (blocks--) {
        SHA256_Transform(&hash, input);
        input += 64;
    }
    memcpy(ccdigest_u8(state), hash.h, sizeof(sha256_initial));
    cc_clear(sizeof(hash), &hash);
}

static void sha512_compress(ccdigest_state_t state, unsigned long blocks, const void *data)
{
    SHA512_CTX hash = {0};
    const unsigned char *input = data;
    memcpy(hash.h, ccdigest_u8(state), sizeof(sha512_initial));
    while (blocks--) {
        SHA512_Transform(&hash, input);
        input += 128;
    }
    memcpy(ccdigest_u8(state), hash.h, sizeof(sha512_initial));
    cc_clear(sizeof(hash), &hash);
}

static void store_word(unsigned char *out, uint64_t value, unsigned size, int little)
{
    for (unsigned i = 0; i < size; ++i)
        out[little ? i : size - 1 - i] = value >> (i * 8);
}

/* Padding and serialization use Darwin's fixed digest-context layout. */
static void finish(const struct ccdigest_info *di, ccdigest_ctx_t ctx,
    unsigned char *output, unsigned word_size, int little)
{
    unsigned char *buffer = ccdigest_data(di, ctx);
    unsigned length_size = di->block_size == 128 ? 16 : 8;
    unsigned used = ccdigest_num(di, ctx);
    uint64_t bits = ccdigest_nbits(di, ctx) + (uint64_t)used * 8;
    buffer[used++] = 0x80;
    if (used > di->block_size - length_size) {
        memset(buffer + used, 0, di->block_size - used);
        di->compress(ccdigest_state(di, ctx), 1, buffer);
        used = 0;
    }
    memset(buffer + used, 0, di->block_size - used);
    store_word(buffer + di->block_size - 8, bits, 8, little);
    di->compress(ccdigest_state(di, ctx), 1, buffer);
    ccdigest_nbits(di, ctx) = bits;
    for (unsigned i = 0; i < di->output_size / word_size; ++i) {
        uint64_t value = word_size == 8 ? ccdigest_state_u64(di, ctx)[i] :
            ccdigest_state_u32(di, ctx)[i];
        store_word(output + i * word_size, value, word_size, little);
    }
}

static void md5_final(const struct ccdigest_info *di, ccdigest_ctx_t ctx, unsigned char *out)
{
    finish(di, ctx, out, 4, 1);
}

static void sha512_final(const struct ccdigest_info *di, ccdigest_ctx_t ctx, unsigned char *out)
{
    finish(di, ctx, out, 8, 0);
}

const struct ccdigest_info cp_md5 = {
    16, 16, 64, sizeof(CC_DIGEST_OID_MD5) - 1, (unsigned char *)CC_DIGEST_OID_MD5, md5_initial, md5_compress, md5_final};
const struct ccdigest_info cp_sha256 = {
    32, 32, 64, ccoid_sha256_len, (unsigned char *)CC_DIGEST_OID_SHA256,
    sha256_initial, sha256_compress, ccdigest_final_64be};
const struct ccdigest_info cp_sha384 = {
    48, 64, 128, ccoid_sha384_len, (unsigned char *)CC_DIGEST_OID_SHA384,
    sha384_initial, sha512_compress, sha512_final};
const struct ccdigest_info cp_sha512 = {
    64, 64, 128, ccoid_sha512_len, (unsigned char *)CC_DIGEST_OID_SHA512,
    sha512_initial, sha512_compress, sha512_final};
