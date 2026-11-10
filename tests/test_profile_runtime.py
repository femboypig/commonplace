"""Exercise the pinned compiler-rt serializer with actual counter data."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProfileBufferTests(unittest.TestCase):
    def test_counter_payload_header_and_padding(self):
        source = ROOT / 'sources/compiler_rt/lib/profile'
        if not source.is_dir():
            self.skipTest('run make fetch to obtain compiler-rt')
        (ROOT / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'build', prefix='test-profile-') as directory:
            directory = Path(directory)
            subprocess.run(['clang', '-std=gnu99', '-I' + str(source),
                            str(source / 'InstrProfiling.c'),
                            str(source / 'InstrProfilingBuffer.c'),
                            str(source / 'InstrProfilingPlatformOther.c'),
                            str(ROOT / 'tests/profile-probe.c'),
                            '-o', str(directory / 'probe')], check=True)
            subprocess.run([str(directory / 'probe')], check=True)
