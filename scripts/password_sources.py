"""Select OpenSSL's original SHA-crypt implementation without its command frontend."""


def sha_crypt(original):
    license_text = original[: original.index("#include")]
    constants = original[
        original.index("static const unsigned char cov_2char[") : original.index(
            "typedef enum {"
        )
    ]
    start = original.index("static char *shacrypt(")
    end = original.index("\nstatic int do_passwd(", start)
    algorithm = original[start:end].replace(
        "static char *shacrypt(", "char *commonplace_shacrypt(", 1
    )
    return (
        license_text
        + """
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/bio.h>
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/sha.h>
"""
        + constants
        + algorithm
    )
