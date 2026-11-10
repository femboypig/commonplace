#!/usr/bin/env bash
set -euo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"
mkdir -p build/openssl build/crypto toolchain/lib
if [[ ! -f build/openssl/Makefile ]]; then
    (
        cd build/openssl
        perl ../../sources/openssl/Configure darwin64-x86_64-cc \
            no-asm no-shared no-threads no-dso no-engine no-module \
            no-tests no-stdio no-ui-console no-zlib
    )
fi
make -C build/openssl -j2 build_generated > build/crypto/generated.log 2>&1
resource_dir=$(clang -print-resource-dir)
output=build/crypto
compiler=(toolchain/bin/x86_64-apple-darwin15-clang)
target_flags=(-mkernel -DKERNEL -nostdinc -I"$resource_dir/include"
    -Icompat/crypto -Isources/xnu/bsd -Isources/xnu/libkern -Isources/xnu/EXTERNAL_HEADERS)
if [[ ${1:-} == --host ]]; then
    output=build/crypto-host
    compiler=(clang)
    target_flags=(-fPIC)
elif [[ $# != 0 ]]; then
    echo 'usage: build-crypto.sh [--host]' >&2
    exit 2
fi
mkdir -p "$output"
sources=(aes/aes_core des/set_key des/des_enc des/ecb_enc des/ecb3_enc \
    bf/bf_enc bf/bf_skey bf/bf_ecb cast/c_enc cast/c_skey cast/c_ecb \
    rc4/rc4_enc rc4/rc4_skey md5/md5_dgst sha/sha256 sha/sha512 modes/gcm128)
objects=()
for source in "${sources[@]}"; do
    object="$output/${source//\//-}.o"
    "${compiler[@]}" -std=gnu11 -O2 -g \
        -ffreestanding -fno-builtin -fno-stack-protector -fno-strict-aliasing \
        -DOPENSSL_AES_CONST_TIME -include compat/crypto/namespace.h "${target_flags[@]}" \
        -msoft-float -mno-sse -mno-sse2 -mno-mmx -mno-red-zone \
        -Ibuild/openssl/include -Isources/openssl/include -Isources/openssl \
        -c "sources/openssl/crypto/$source.c" -o "$object"
    objects+=("$object")
done
if [[ ${1:-} == --host ]]; then
    ar rcs "$output/libcrypto.a" "${objects[@]}"
else
    toolchain/bin/x86_64-apple-darwin15-libtool -static \
        -o toolchain/lib/libkernel_crypto.a "${objects[@]}"
fi
