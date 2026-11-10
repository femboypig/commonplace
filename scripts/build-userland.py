#!/usr/bin/env python3
"""Build a static Darwin bootstrap init using XNU's syscall numbers."""
import re
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'build/userland'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    master = (ROOT / 'sources/xnu/bsd/kern/syscalls.master').read_text()
    entries = []
    for name in ('read', 'write', 'open', 'close', 'getpid', 'select'):
        match = re.search(r'^(\d+)\s+[^\n]*\b' + name + r'\(', master, re.M)
        if not match:
            raise ValueError('missing syscall: ' + name)
        entries.append(f'#define SYS_{name} {match[1]}\n')
    (OUT / 'syscall-numbers.h').write_text(''.join(entries))
    objects = []
    for source in sorted((ROOT / 'userland').rglob('*')):
        if source.suffix not in ('.c', '.S'):
            continue
        output = OUT / (source.stem + '.o')
        subprocess.run([str(ROOT / 'toolchain/bin/x86_64-apple-darwin15-clang'),
                        '-std=c11', '-O2', '-g', '-Wall', '-Wextra', '-Werror',
                        '-ffreestanding', '-fno-builtin', '-fno-stack-protector',
                        '-fno-pic', '-fno-pie', '-I' + str(ROOT / 'userland/include'),
                        '-I' + str(OUT), '-c', str(source), '-o', str(output)], check=True)
        objects.append(str(output))
    subprocess.run([str(ROOT / 'toolchain/bin/x86_64-apple-darwin15-ld'),
                    '-static', '-arch', 'x86_64', '-macosx_version_min', '10.11',
                    '-e', '_start', '-no_uuid', '-o', str(OUT / 'init'), *objects], check=True)


if __name__ == '__main__':
    main()
