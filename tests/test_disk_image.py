"""A build must never format over an existing persistent disk."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent


class DiskImageTest(unittest.TestCase):
    def test_creation_preserves_existing_data_and_rejects_unrecognized_images(self):
        if not (ROOT/'toolchain/bin/newfs_hfs').is_file(): self.skipTest('run make rootfs-tools first')
        with tempfile.TemporaryDirectory(prefix='commonplace-disk-') as temporary:
            disk=Path(temporary)/'data.hfs'
            command=['python3',str(ROOT/'scripts/create-disk.py'),'--path',str(disk),'--size','16']
            subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
            initial=hashlib.sha256(disk.read_bytes()).digest()
            subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
            self.assertEqual(initial,hashlib.sha256(disk.read_bytes()).digest())
            invalid=Path(temporary)/'existing'
            invalid.write_bytes(b'preserve this existing file')
            result=subprocess.run(['python3',str(ROOT/'scripts/create-disk.py'),'--path',str(invalid)],
                                  capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(invalid.read_bytes(),b'preserve this existing file')
