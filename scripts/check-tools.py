#!/usr/bin/env python3
"""Exercise the cross toolchain; these artifacts are not a bootable kernel."""

from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / 'toolchain' / 'bin'


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def main():
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=build, prefix='check-tools-') as directory:
        directory = Path(directory)
        (directory / 'entry.c').write_text('void entry(void) { for (;;) {} }\n')
        run(str(BIN / 'x86_64-apple-darwin15-clang'), '-ffreestanding',
            '-fno-stack-protector', '-fno-asynchronous-unwind-tables',
            '-c', 'entry.c', '-o', 'entry.o', cwd=directory)
        # XNU requires the kernel linker path, including MH_EXECUTE and a
        # high virtual address; a dylib-only link test would miss this.
        run(str(BIN / 'x86_64-apple-darwin15-ld'), '-arch', 'x86_64',
            '-static', '-e', '_entry', '-image_base', '0xffffff8000200000',
            '-o', 'kernel-probe', 'entry.o', cwd=directory)
        header = (directory / 'kernel-probe').read_bytes()[:32]
        magic, cpu, _, file_type, *_ = struct.unpack('<8I', header)
        if (magic, cpu, file_type) != (0xFEEDFACF, 0x01000007, 2):
            raise RuntimeError('linker did not produce an x86_64 Mach-O executable')
        print('mach-o: freestanding x86_64 kernel link passed')
        run(str(BIN / 'x86_64-apple-darwin15-clang'), '-nostdlib',
            '-fuse-ld=' + str(BIN / 'x86_64-apple-darwin15-ld'),
            '-Wl,-static,-e,_entry,-image_base,0xffffff8000200000',
            'entry.o', '-o', 'kernel-driver-probe', cwd=directory)
        driver_header = (directory / 'kernel-driver-probe').read_bytes()[:32]
        if struct.unpack('<4I', driver_header[:16])[:2] != (0xFEEDFACF, 0x01000007):
            raise RuntimeError('compiler driver selected an incorrect linker target')
        print('mach-o: compiler driver uses the local darwin linker')


        # No SDK is needed for this definition; it exercises the generator,
        # its preprocessor, request/reply numbering and variable-length arrays.
        (directory / 'probe.defs').write_text('''\
subsystem commonplace_probe 48000;
type mach_port_t = MACH_MSG_TYPE_COPY_SEND;
type integer_t = MACH_MSG_TYPE_INTEGER_32;
type byte_array_t = array[*:64] of MACH_MSG_TYPE_BYTE;
routine probe(port: mach_port_t; value: integer_t; out bytes: byte_array_t);
''')
        run(str(BIN / 'mig'), 'probe.defs', cwd=directory)
        for filename in ('commonplace_probe.h', 'commonplace_probeUser.c',
                         'commonplace_probeServer.c'):
            content = (directory / filename).read_text()
            if 'probe' not in content:
                raise RuntimeError(f'empty MIG output: {filename}')
        server = (directory / 'commonplace_probeServer.c').read_text()
        if '48000' not in server or 'msgh_id + 100' not in server:
            raise RuntimeError('unexpected MIG request/reply IDs')
        print('mig: request/reply interface generation passed')

        (directory / 'broken.defs').write_text('#include "missing-header.h"\n')
        failure = subprocess.run([str(BIN / 'mig'), 'broken.defs'], cwd=directory,
                                 capture_output=True, text=True)
        if failure.returncode == 0:
            raise RuntimeError('MIG hid a preprocessor failure')
        print('mig: preprocessor failures propagate')


if __name__ == '__main__':
    main()
