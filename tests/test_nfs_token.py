"""Run the patched XNU parser with a controlled decryption callback."""

import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class KerberosOidTests(unittest.TestCase):
    def test_parser_checks_every_oid_byte_before_decryption(self):
        spec = importlib.util.spec_from_file_location('xnu_build', ROOT / 'scripts/build-xnu.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=ROOT / 'build', prefix='test-nfs-') as directory:
            directory = Path(directory)
            source = ROOT / 'sources/xnu/bsd/nfs/nfs_gss.c'
            if not source.is_file():
                self.skipTest('run make fetch to obtain the pinned XNU source')
            (directory / 'bsd/nfs').mkdir(parents=True)
            (directory / 'bsd/nfs/nfs_gss.c').write_bytes(source.read_bytes())
            module.apply_source_patches(directory)
            text = (directory / 'bsd/nfs/nfs_gss.c').read_text()
            functions = []
            for name in ('nfs_gss_der_length_get', 'nfs_gss_token_get'):
                functions.append(re.search(r'static int\n' + name + r'\(.*?\n}\n',
                                           text, re.DOTALL).group())
            oid = re.search(r'u_char krb5_mech\[11\] = \{[^}]+};', text).group()
            harness = (ROOT / 'tests/nfs-token-probe.c').read_text()
            harness = harness.replace('/* XNU_PARSER */', oid + '\n' + '\n'.join(functions))
            (directory / 'probe.c').write_text(harness)
            subprocess.run(['clang', '-std=gnu99', '-Werror=memsize-comparison',
                            str(directory / 'probe.c'), '-o', str(directory / 'probe')], check=True)
            subprocess.run([str(directory / 'probe')], check=True)
