"""Kernel C must not acquire SIMD instructions before FPU initialization."""

import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class KernelSimdTest(unittest.TestCase):
    def test_aggregate_copies_use_general_registers(self):
        if not (ROOT / 'sources/xnu/makedefs/MakeInc.def').is_file():
            self.skipTest('run make fetch first')
        spec = importlib.util.spec_from_file_location('xnu_build', ROOT / 'scripts/build-xnu.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix='commonplace-simd-test-') as directory:
            directory = Path(directory)
            module.apply_source_patches(directory)
            definitions = (directory / 'makedefs/MakeInc.def').read_text().replace('\\\n', ' ')
            flags = re.search(r'^CFLAGS_X86_64\s*=([^\n]+)', definitions, re.M).group(1).split()
            source = directory / 'copy.c'
            source.write_text('''\
struct value {
    unsigned height, width, depth, stride;
    unsigned long base;
    unsigned type;
    char name[32];
    unsigned long physical;
    unsigned rows, columns, scan, scale, rotate, reserved[3];
};
extern struct value state;
extern unsigned adjust(unsigned value);
void update(struct value *output, unsigned height) {
    struct value local = state;
    local.height = height;
    local.type = adjust(height);
    *output = local;
}
''')
            compiler = ROOT / 'toolchain/bin/x86_64-apple-darwin15-clang'
            for language, extension in [('c', 'c'), ('c++', 'cpp')]:
                output = directory / (extension + '.s')
                subprocess.run([str(compiler), '-x', language, '-O2', '-ffreestanding',
                                '-fno-builtin', *flags, '-S', str(source), '-o', str(output)],
                               check=True)
                self.assertNotRegex(output.read_text(), r'%(?:xmm|ymm|zmm|mm)[0-9]')

            # TCP cubic intentionally uses the floating-point ABI after boot.
            source.write_text('float cube(float value) { return value * value * value; }\n')
            definitions = (directory / 'bsd/conf/Makefile.template').read_text()
            for name in ('tcp_cubic', 'cbrtf'):
                extra = re.search(r'^' + name + r'\.o_CFLAGS_ADD\s*\+=([^\n]+)',
                                  definitions, re.M).group(1).split()
                subprocess.run([str(compiler), '-x', 'c', '-O2', *flags, *extra,
                                '-c', str(source), '-o', str(directory / (name + '.o'))],
                               check=True)
