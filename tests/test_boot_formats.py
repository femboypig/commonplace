import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class BootFormatsTest(unittest.TestCase):
    def test_bounds_and_wire_formats(self):
        with tempfile.TemporaryDirectory(prefix='commonplace-boot-test-') as directory:
            probe = pathlib.Path(directory) / 'probe'
            subprocess.run([
                'gcc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                '-I', str(ROOT / 'boot'), str(ROOT / 'boot/image.c'),
                str(ROOT / 'boot/tree.c'), str(ROOT / 'tests/boot-format-probe.c'),
                '-o', str(probe),
            ], check=True)
            subprocess.run([str(probe)], check=True)
