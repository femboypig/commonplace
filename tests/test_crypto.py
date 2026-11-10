from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


class CryptoProviderTest(unittest.TestCase):
    def test_darwin_abi_known_answers_and_streaming(self):
        if not (ROOT / 'sources/openssl/Configure').is_file():
            self.skipTest('run make fetch first')
        subprocess.run(['python3', str(ROOT / 'scripts/check-crypto.py')], check=True)
