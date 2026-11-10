#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <strings.h>
#include <sys/types.h>

typedef int gss_key_info;
typedef unsigned char des_cblock[8];
#define AUTH_BADCRED 1
#define KRB5_SZ_ALG 8
#define DES_DECRYPT 0
#define KG_USAGE_SEQ 0
#define HASHLEN(key) 8

static int decryptions;
static void gss_des_crypt(gss_key_info *key, des_cblock *input,
    des_cblock *output, int count, des_cblock *iv, void *unused, int mode, int usage)
{
    ++decryptions;
    memset(output, 0, count);
}

/* XNU_PARSER */

int main(void)
{
    unsigned char token[64] = {0x60, 35};
    unsigned char algorithm[8] = {0};
    unsigned char checksum[8];
    uint32_t length = 0;
    gss_key_info key = 0;
    memcpy(token + 2, krb5_mech, sizeof(krb5_mech));
    assert(nfs_gss_token_get(&key, algorithm, token, 1, &length, checksum) == 0);
    assert(decryptions == 1);
    assert(length == 2 + sizeof(krb5_mech) + KRB5_SZ_ALG + 8 + HASHLEN(&key));
    for (unsigned int i = 0; i < sizeof(krb5_mech); ++i) {
        token[2 + i] ^= 1;
        assert(nfs_gss_token_get(&key, algorithm, token, 1, &length, checksum) == AUTH_BADCRED);
        assert(decryptions == 1);
        token[2 + i] ^= 1;
    }
    return 0;
}
