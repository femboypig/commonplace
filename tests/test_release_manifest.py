"""Release verification must reject changed boot code and permit saved user data."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent


class ReleaseManifestTest(unittest.TestCase):
    def test_immutable_and_mutable_artifacts(self):
        spec=importlib.util.spec_from_file_location('release_verify',ROOT/'scripts/verify-release.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix='commonplace-release-') as temporary:
            directory=Path(temporary)
            code=directory/'kernel';code.write_bytes(b'kernel image')
            data=directory/'data';data.write_bytes(b'initial data')
            manifest={'schema':1,'immutable':{'kernel':hashlib.sha256(code.read_bytes()).hexdigest()},
                      'mutable':{'data':{}}}
            (directory/'manifest.json').write_text(json.dumps(manifest))
            module.verify(directory)
            data.write_bytes(b'saved user files');module.verify(directory)
            code.write_bytes(b'damaged kernel')
            with self.assertRaises(ValueError):module.verify(directory)
            manifest['immutable']={'../outside':'0'*64}
            (directory/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):module.verify(directory)
