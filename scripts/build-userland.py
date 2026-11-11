#!/usr/bin/env python3
"""Build static Darwin programs against XNU's syscall ABI."""
import json
import re
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'build/userland'
SYSCALLS = ('exit', 'fork', 'read', 'write', 'open', 'close', 'wait4', 'unlink', 'chdir',
            'getpid', 'getuid', 'sync', 'kill', 'dup', 'pipe', 'sigaction', 'ioctl', 'execve',
            'dup2', 'fcntl', 'select', 'mkdir', 'rmdir', 'setsid', 'mount', 'sysctl',
            'getdirentries64', 'gettimeofday', 'sigreturn')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    master = (ROOT / 'sources/xnu/bsd/kern/syscalls.master').read_text()
    entries = []
    for name in SYSCALLS:
        match = re.search(r'^(\d+)\s+[^\n]*\b' + name + r'\(', master, re.M)
        if not match:
            raise ValueError('missing syscall: ' + name)
        entries.append(f'#define SYS_{name} {match[1]}\n')
    (OUT / 'syscall-numbers.h').write_text(''.join(entries))
    library = ROOT / 'userland/lib'
    common = sorted(library.glob('*.c')) + sorted(library.glob('*.S'))
    programs = {'init': sorted((ROOT / 'userland/init').glob('*.c')),
                'sh': sorted((ROOT / 'userland/sh').glob('*.c'))}
    programs.update({path.stem: [path] for path in sorted((ROOT / 'userland/bin').glob('*.c'))})
    objects = {}
    for source in sorted(set(common + [path for paths in programs.values() for path in paths])):
        output = OUT / 'obj' / source.relative_to(ROOT / 'userland').with_suffix('.o')
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(ROOT / 'toolchain/bin/x86_64-apple-darwin15-clang'),
                        '-std=c11', '-O2', '-g', '-Wall', '-Wextra', '-Werror',
                        '-ffreestanding', '-fno-builtin', '-fno-stack-protector',
                        '-fno-pic', '-fno-pie', '-I' + str(ROOT / 'userland/include'),
                        '-I' + str(OUT), '-c', str(source), '-o', str(output)], check=True)
        objects[source] = output
    for name, sources in programs.items():
        subprocess.run([str(ROOT / 'toolchain/bin/x86_64-apple-darwin15-ld'),
                        '-static', '-arch', 'x86_64', '-macosx_version_min', '10.11',
                        '-e', '_start', '-no_uuid', '-o', str(OUT / name),
                        *[str(objects[source]) for source in common + sources]], check=True)
    (OUT / 'programs.json').write_text(json.dumps(list(programs), indent=2) + '\n')


if __name__ == '__main__':
    main()
