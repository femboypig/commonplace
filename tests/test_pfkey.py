"""Check the real initial PF_KEY framing guard before request dispatch."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PfkeyLengthTests(unittest.TestCase):
    def test_header_length_matches_packet_length(self):
        if not (ROOT / 'sources/xnu/bsd/netkey/key.c').is_file():
            self.skipTest('run make fetch to obtain the pinned XNU source')
        spec = importlib.util.spec_from_file_location('xnu_build', ROOT / 'scripts/build-xnu.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=ROOT / 'build', prefix='test-pfkey-') as directory:
            directory = Path(directory)
            module.apply_source_patches(directory)
            source = (directory / 'bsd/netkey/key.c').read_text()
            prefix = source[source.index('int\nkey_parse('):].split(
                '\n\tif (msg->sadb_msg_version', 1)[0]
            prefix += '\nreturn 0;\nsenderror:\nreturn error;\n}\n'
            harness = (ROOT / 'tests/pfkey-probe.c').read_text().replace('/* XNU_FRAMING */', prefix)
            (directory / 'probe.c').write_text(harness)
            subprocess.run(['clang', '-std=gnu99', '-Werror=tautological-compare',
                            str(directory / 'probe.c'), '-o', str(directory / 'probe')], check=True)
            subprocess.run([str(directory / 'probe')], check=True)
