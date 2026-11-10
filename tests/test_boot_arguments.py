"""Validate the RAM-disk handoff against Darwin's boot argument ABI."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class BootArgumentsTest(unittest.TestCase):
    def test_root_property_and_memory_lifetime(self):
        with tempfile.TemporaryDirectory(prefix='commonplace-arguments-') as directory:
            output = Path(directory) / 'probe'
            sources = [ROOT / 'boot' / (name + '.c') for name in ('arguments', 'tree', 'memory')]
            subprocess.run(['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            '-I' + str(ROOT / 'sources/xnu/pexpert'), '-I' + str(ROOT / 'boot'),
                            str(ROOT / 'tests/boot-arguments-probe.c'), *map(str, sources),
                            '-o', str(output)], check=True)
            subprocess.run([str(output)], check=True)
