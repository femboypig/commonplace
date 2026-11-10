"""Compare the patched kernel sorter with libc across layouts and alignments."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class KernelSortTests(unittest.TestCase):
    def test_aligned_and_unaligned_records_match_libc(self):
        if not (ROOT / 'sources/xnu/bsd/kern/qsort.c').is_file():
            self.skipTest('run make fetch to obtain the pinned XNU source')
        spec = importlib.util.spec_from_file_location('xnu_build', ROOT / 'scripts/build-xnu.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=ROOT / 'build', prefix='test-qsort-') as directory:
            directory = Path(directory)
            module.apply_source_patches(directory)
            include = directory / 'include/sys'
            include.mkdir(parents=True)
            (include / 'kpi_private.h').symlink_to(ROOT / 'sources/xnu/bsd/sys/kpi_private.h')
            subprocess.run(['clang', '-std=gnu99', '-Werror=null-pointer-subtraction',
                            '-D__private_extern__=', '-Dqsort=commonplace_qsort',
                            '-I' + str(include.parent), '-c', str(directory / 'bsd/kern/qsort.c'),
                            '-o', str(directory / 'qsort.o')], check=True)
            subprocess.run(['clang', '-std=gnu99', str(ROOT / 'tests/qsort-probe.c'),
                            str(directory / 'qsort.o'), '-o', str(directory / 'probe')], check=True)
            subprocess.run([str(directory / 'probe')], check=True)
