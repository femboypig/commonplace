#!/usr/bin/env python3
"""Validate the linked kernel and record the exact local build artifact."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
KERNEL = ROOT / 'build/xnu/obj/DEVELOPMENT_X86_64/kernel.development'


def check_pthread_sysctls(image, segments, nm, symbol_file):
    output = subprocess.check_output([str(nm), '-n', str(symbol_file)], text=True)
    addresses = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) == 3:
            addresses[fields[2]] = int(fields[0], 16)
    suffixes = ('wq_yielded_threshold', 'wq_yielded_window_usecs',
                'wq_stalled_window_usecs', 'wq_reduce_pool_window_usecs',
                'wq_max_timer_interval_usecs', 'wq_max_threads',
                'wq_max_constrained_threads', 'pthread_debug_tracing')
    names = {'_sysctl__kern_' + suffix for suffix in suffixes}
    names.update(name for name in ('_sysctl__kern_wq_max_concurrency',
                                  '_sysctl__debug_wq_kevent_test') if name in addresses)
    for name in sorted(names):
        address = addresses.get(name)
        segment = next((s for s in segments if address is not None and
                        s['address'] <= address and
                        address + 24 <= s['address'] + s['file_size']), None)
        if segment is None:
            raise ValueError('missing pthread sysctl descriptor: ' + name)
        # x86_64 struct sysctl_oid: two pointers, oid_number, then oid_kind.
        offset = segment['file_offset'] + address - segment['address'] + 20
        kind = struct.unpack_from('<I', image, offset)[0]
        if not kind & 0x02000000:  # CTLFLAG_NOAUTO in Darwin 15 sys/sysctl.h
            raise ValueError('pthread sysctl would be registered twice: ' + name)
    return len(names)


def main():
    image = KERNEL.read_bytes()
    if len(image) < 32:
        raise ValueError('truncated Mach-O header')
    magic, cpu, _, kind, commands, command_bytes, flags, _ = struct.unpack_from('<8I', image)
    if (magic, cpu, kind) != (0xFEEDFACF, 0x01000007, 2) or not flags & 1:
        raise ValueError('expected an x86_64 Mach-O executable without undefined symbols')
    limit = 32 + command_bytes
    if limit > len(image):
        raise ValueError('load commands exceed the file')
    cursor, entry = 32, None
    segments = []
    for _ in range(commands):
        if cursor + 8 > limit:
            raise ValueError('truncated load command')
        command, size = struct.unpack_from('<II', image, cursor)
        if size < 8 or size % 8 or cursor + size > limit:
            raise ValueError('invalid load command size')
        if command == 0x19:
            if size < 72:
                raise ValueError('truncated segment command')
            values = struct.unpack_from('<II16sQQQQiiII', image, cursor)
            _, _, name, address, memory_size, offset, file_size, _, _, sections, _ = values
            if size != 72 + 80 * sections or file_size > memory_size or offset + file_size > len(image):
                raise ValueError('invalid Mach-O segment bounds')
            segments.append({'name': name.rstrip(b'\0').decode('ascii'),
                             'address': address, 'size': memory_size,
                             'file_offset': offset, 'file_size': file_size})
        elif command == 5:
            if size < 184:
                raise ValueError('truncated x86_64 thread state')
            flavor, count = struct.unpack_from('<II', image, cursor + 8)
            if (flavor, count) != (4, 42):
                raise ValueError('unsupported kernel thread state')
            entry = struct.unpack_from('<Q', image, cursor + 16 + 16 * 8)[0]
        cursor += size
    if cursor != limit:
        raise ValueError('load command count and size disagree')
    loaded = [segment for segment in segments if segment['size']]
    if entry is None or not any(s['address'] <= entry < s['address'] + s['file_size'] for s in loaded):
        raise ValueError('kernel entry is outside loaded file data')
    ordered = sorted(loaded, key=lambda s: s['address'])
    for left, right in zip(ordered, ordered[1:]):
        if left['address'] + left['size'] > right['address']:
            raise ValueError('overlapping kernel segments')
    for name in ('__TEXT', '__DATA', '__HIB', '__LINKEDIT'):
        if name not in {segment['name'] for segment in loaded}:
            raise ValueError(f'missing required segment: {name}')
    if b'Darwin Kernel Version 15.6.0' not in image or b'__mod_term_func' not in image:
        raise ValueError('unexpected kernel version or missing C++ termination table')
    nm = ROOT / 'toolchain/bin/x86_64-apple-darwin15-nm'
    symbol_file = KERNEL.with_name(KERNEL.name + '.unstripped')
    undefined = subprocess.check_output([str(nm), '-u', str(symbol_file)], text=True).strip()
    if undefined:
        raise ValueError('kernel has unresolved symbols: ' + undefined)
    symbols = set(subprocess.check_output([str(nm), '-gj', str(symbol_file)], text=True).splitlines())
    if not {'__start', '_pstart', '_kernel_bootstrap', '_bsd_init', '_version',
            '__ZN19CommonplacePlatform5startEP9IOService',
            '__ZN19CommonplacePlatform9metaClassE',
            '_pthread_start', '_pthread_internal_functions', '__pthread_init',
            '_commonplace_crypto_init', '_cp_crypto_selftest', '_AES_encrypt',
            '_cp_openssl_SHA256_Transform', '_CRYPTO_gcm128_encrypt'} <= symbols:
        raise ValueError('required kernel entry points are missing')
    pthread_sysctls = check_pthread_sysctls(image, segments, nm, symbol_file)
    metadata = {
        'kernel': str(KERNEL.relative_to(ROOT)), 'version': '15.6.0',
        'size': len(image), 'sha256': hashlib.sha256(image).hexdigest(),
        'entry': entry, 'entry_physical': entry & 0xFFFFFFFF,
        'segments': segments,
        'pthread_sysctls': pthread_sysctls,
        'sources': json.loads((ROOT / 'sources.lock.json').read_text()),
        'patches': {str(path.relative_to(ROOT / 'patches')):
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted((ROOT / 'patches').rglob('*.patch'))},
        'crypto_archive_sha256': hashlib.sha256(
            (ROOT / 'toolchain/lib/libkernel_crypto.a').read_bytes()).hexdigest(),
        'kernel_sources': {
            str(path.relative_to(ROOT / 'build/xnu-source/commonplace')):
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / 'build/xnu-source/commonplace').rglob('*'))
            if path.is_file()
        },
        'compiler': subprocess.check_output(['clang', '--version'], text=True).splitlines()[0],
    }
    (ROOT / 'build/kernel.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(f'xnu: Darwin 15.6.0, {len(image)} bytes, entry {entry:#x}, no undefined symbols')


if __name__ == '__main__':
    main()
