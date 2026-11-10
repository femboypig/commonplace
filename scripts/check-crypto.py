#!/usr/bin/env python3
"""Check Darwin crypto adapters against independent digest and cipher vectors."""

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def literal(data):
    return '(const unsigned char *)"' + ''.join(f'\\x{byte:02x}' for byte in data) + '"'


def digest_vectors(directory):
    digests, hmacs = [], []
    for index, name in enumerate(('md5', 'sha1', 'sha256', 'sha384', 'sha512')):
        for size in (0, 1, 3, 55, 56, 63, 64, 65, 111, 112, 127, 128, 129, 255, 1024):
            message = bytes((i * 73 + 19) % 256 for i in range(size))
            expected = hashlib.new(name, message).digest()
            digests.append(f'{{{index}, {literal(message)}, {size}, {literal(expected)}}}')
        block = hashlib.new(name).block_size
        for key_size in (0, 1, block - 1, block, block + 1, 200):
            key = bytes((i * 31 + 7) % 256 for i in range(key_size))
            message = bytes(range(137))
            expected = hmac.new(key, message, name).digest()
            hmacs.append(f'{{{index}, {literal(key)}, {key_size}, {literal(message)}, '
                         f'{len(message)}, {literal(expected)}}}')
    (directory / 'digest-vectors.h').write_text(
        'static const struct digest_vector digests[] = {\n' + ',\n'.join(digests) + '\n};\n' +
        'static const struct hmac_vector hmacs[] = {\n' + ',\n'.join(hmacs) + '\n};\n')
    return len(digests), len(hmacs)


def cipher_vectors(directory):
    names = {f'AES-{bits}-{mode}': f'AES_{mode}'
             for bits in (128, 192, 256) for mode in ('ECB', 'CBC', 'GCM', 'XTS')}
    names.update({'DES-ECB': 'DES_ECB', 'DES-CBC': 'DES_CBC',
                  'DES-EDE-ECB': 'DES3_ECB', 'DES-EDE3-ECB': 'DES3_ECB',
                  'DES-EDE-CBC': 'DES3_CBC', 'DES-EDE3-CBC': 'DES3_CBC',
                  'BF-ECB': 'BLOWFISH_ECB', 'CAST5-ECB': 'CAST_ECB', 'RC4': 'RC4_STREAM'})
    vectors, counts = [], {}
    source = ROOT / 'sources/openssl/test/recipes/30-test_evp_data'
    for path in sorted(source.glob('evpciph_*.txt')):
        content = '\n'.join(line for line in path.read_text().splitlines()
                            if not line.lstrip().startswith('#'))
        for block in re.split(r'\n\s*\n', content):
            fields = dict(line.split(' = ', 1) for line in block.splitlines() if ' = ' in line)
            name = fields.get('Cipher', '').upper()
            if name not in names or 'Result' in fields or counts.get(name, 0) >= 8:
                continue
            try:
                key, iv, aad, plain, cipher, tag = (
                    bytes.fromhex(fields.get(field, '')) for field in
                    ('Key', 'IV', 'AAD', 'Plaintext', 'Ciphertext', 'Tag'))
            except ValueError:
                continue
            mode = names[name]
            if not key or len(plain) != len(cipher) or len(plain) > 4096:
                continue
            if mode == 'AES_GCM':
                if not iv or not tag or len(tag) > 16: continue
            elif not plain:
                continue
            if mode.endswith(('ECB', 'CBC', 'XTS')):
                size = 16 if mode.startswith('AES_') else 8
                if len(plain) % size: continue
                if mode.endswith(('CBC', 'XTS')) and len(iv) != size: continue
            counts[name] = counts.get(name, 0) + 1
            values = [mode, literal(key), str(len(key)), literal(iv), str(len(iv)),
                      literal(aad), str(len(aad)), literal(plain), literal(cipher),
                      str(len(plain)), literal(tag), str(len(tag))]
            vectors.append('{' + ', '.join(values) + '}')
    required = set(names.values())
    actual = {names[name] for name in counts}
    if actual != required:
        raise ValueError(f'missing cipher-vector modes: {required - actual}')
    (directory / 'cipher-vectors.h').write_text(
        'static const struct cipher_vector ciphers[] = {\n' + ',\n'.join(vectors) + '\n};\n')
    return len(vectors)


def main():
    subprocess.run(['bash', str(ROOT / 'scripts/build-crypto.sh'), '--host'], check=True)
    with tempfile.TemporaryDirectory(dir=ROOT / 'build', prefix='crypto-check-') as temporary:
        directory = Path(temporary)
        include = directory / 'include'
        (include / 'libkern').mkdir(parents=True)
        (include / 'corecrypto').symlink_to(ROOT / 'sources/xnu/EXTERNAL_HEADERS/corecrypto')
        (include / 'libkern/crypto').symlink_to(ROOT / 'sources/xnu/libkern/libkern/crypto')
        digest_count, hmac_count = digest_vectors(directory)
        cipher_count = cipher_vectors(directory)
        flags = ['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra',
                 '-Werror=implicit-function-declaration', '-fno-strict-aliasing',
                 '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                 '-D__private_extern__=', '-DOPENSSL_SUPPRESS_DEPRECATED',
                 '-DCOMMONPLACE_CRYPTO_HOST', '-I' + str(include), '-I' + str(directory),
                 '-I' + str(ROOT / 'kernel/crypto'), '-I' + str(ROOT / 'build/openssl/include'),
                 '-I' + str(ROOT / 'sources/openssl/include')]
        core = ROOT / 'sources/xnu/osfmk/corecrypto'
        sources = list((ROOT / 'kernel/crypto').glob('*.c'))
        sources += [ROOT / 'sources/xnu/libkern/crypto/register_crypto.c']
        for component in ('cc', 'ccn', 'ccdigest', 'cchmac', 'ccsha1'):
            sources += list((core / component / 'src').glob('*.c'))
        patched = directory / 'patched'
        for name in ('init', 'final'):
            relative = Path(f'osfmk/corecrypto/cchmac/src/cchmac_{name}.c')
            target = patched / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / 'sources/xnu' / relative).read_bytes())
        subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-d', str(patched),
                        '-i', str(ROOT / 'patches/xnu/0023-align-hmac-state-access.patch')],
                       check=True, stdout=subprocess.DEVNULL)
        sources = [patched / source.relative_to(ROOT / 'sources/xnu')
                   if source.name in ('cchmac_init.c', 'cchmac_final.c') else source
                   for source in sources]
        objects = []
        for index, source in enumerate(sources):
            output = directory / f'{index}.o'
            subprocess.run(flags + ['-c', str(source), '-o', str(output)], check=True)
            objects.append(str(output))
        environment = dict(os.environ, ASAN_OPTIONS='detect_leaks=1', UBSAN_OPTIONS='halt_on_error=1')
        for name in ('digest', 'cipher'):
            output = directory / name
            subprocess.run(flags + [str(ROOT / f'tests/crypto-{name}-probe.c'), *objects,
                                    str(ROOT / 'build/crypto-host/libcrypto.a'), '-o', str(output)],
                           check=True)
            subprocess.run([str(output)], check=True, env=environment)
    print(f'crypto: {digest_count} digest, {hmac_count} HMAC and {cipher_count} cipher vectors passed')


if __name__ == '__main__':
    main()
