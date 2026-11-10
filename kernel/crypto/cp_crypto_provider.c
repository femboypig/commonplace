#include "provider.h"
#include <corecrypto/ccsha1.h>
#include <libkern/crypto/aes.h>
#include <libkern/crypto/aesxts.h>
#include <libkern/crypto/des.h>

static void digest_final(const struct ccdigest_info *di, ccdigest_ctx_t ctx, void *output)
{
    di->final(di, ctx, output);
}

static void digest(const struct ccdigest_info *di, unsigned long size,
    const void *input, void *output)
{
    ccdigest_di_decl(di, ctx);
    ccdigest_init(di, ctx);
    ccdigest_update(di, ctx, size, input);
    di->final(di, ctx, output);
    ccdigest_di_clear(di, ctx);
}

static struct crypto_functions functions = {
    .ccdigest_init_fn = ccdigest_init,
    .ccdigest_update_fn = ccdigest_update,
    .ccdigest_final_fn = digest_final,
    .ccdigest_fn = digest,
    .ccmd5_di = &cp_md5,
    .ccsha1_di = &ccsha1_eay_di,
    .ccsha256_di = &cp_sha256,
    .ccsha384_di = &cp_sha384,
    .ccsha512_di = &cp_sha512,
    .cchmac_init_fn = cchmac_init,
    .cchmac_update_fn = cchmac_update,
    .cchmac_final_fn = cchmac_final,
    .cchmac_fn = cchmac,
    .ccaes_ecb_encrypt = &cp_aes_ecb_enc,
    .ccaes_ecb_decrypt = &cp_aes_ecb_dec,
    .ccaes_cbc_encrypt = &cp_aes_cbc_enc,
    .ccaes_cbc_decrypt = &cp_aes_cbc_dec,
    .ccaes_xts_encrypt = &cp_aes_xts_enc,
    .ccaes_xts_decrypt = &cp_aes_xts_dec,
    .ccaes_gcm_encrypt = &cp_aes_gcm_enc,
    .ccaes_gcm_decrypt = &cp_aes_gcm_dec,
    .ccdes_ecb_encrypt = &cp_des_ecb_enc,
    .ccdes_ecb_decrypt = &cp_des_ecb_dec,
    .ccdes_cbc_encrypt = &cp_des_cbc_enc,
    .ccdes_cbc_decrypt = &cp_des_cbc_dec,
    .cctdes_ecb_encrypt = &cp_des3_ecb_enc,
    .cctdes_ecb_decrypt = &cp_des3_ecb_dec,
    .cctdes_cbc_encrypt = &cp_des3_cbc_enc,
    .cctdes_cbc_decrypt = &cp_des3_cbc_dec,
    .ccrc4_info = &cp_rc4,
    .ccblowfish_ecb_encrypt = &cp_blowfish_ecb_enc,
    .ccblowfish_ecb_decrypt = &cp_blowfish_ecb_dec,
    .cccast_ecb_encrypt = &cp_cast_ecb_enc,
    .cccast_ecb_decrypt = &cp_cast_ecb_dec,
    .ccdes_key_is_weak_fn = cp_des_is_weak,
    .ccdes_key_set_odd_parity_fn = cp_des_set_parity,
    /* Darwin 15 never calls its obsolete padding callbacks (which lack a tweak).
     * XNU's XTS interface accepts whole blocks through the descriptors above. */
};

void commonplace_crypto_init(void)
{
    if (cp_aes_cbc_enc.size > sizeof(aes_encrypt_ctx) ||
        cp_aes_cbc_dec.size > sizeof(aes_decrypt_ctx) ||
        cp_aes_xts_enc.size > sizeof(((symmetric_xts *)0)->enc) ||
        cp_des_cbc_enc.size > DES_CBC_CTX_MAX_SIZE ||
        cp_des3_cbc_enc.size > DES3_CBC_CTX_MAX_SIZE)
        cp_crypto_fail("cipher context exceeds Darwin ABI storage");
    cp_digest_prepare();
    cp_crypto_selftest();
    if (register_crypto_functions(&functions) != 0)
        cp_crypto_fail("crypto provider was already registered");
}
