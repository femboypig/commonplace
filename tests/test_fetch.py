import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'fetch.py'
SPEC = importlib.util.spec_from_file_location('source_fetch', MODULE)
FETCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FETCH)


class SourceAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.patch = patch.object(FETCH, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def archive(self, files):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as bundle:
            for name, content in files.items():
                entry = tarfile.TarInfo(name)
                entry.size = len(content)
                bundle.addfile(entry, io.BytesIO(content))
        data = buffer.getvalue()
        checksum = hashlib.sha256(data).hexdigest()
        cache = self.root / '.cache' / 'archives'
        cache.mkdir(parents=True)
        path = cache / (checksum + '.tar.gz')
        path.write_bytes(data)
        return path, {'revision': 'test', 'sha256': checksum,
                      'url': 'https://example.invalid/source.tar.gz'}

    def test_extracts_and_preserves_existing_tree(self):
        _, entry = self.archive({'upstream/code.c': b'int x;',
                                 'upstream/APPLE_LICENSE': b'license'})
        FETCH.fetch('example', entry)
        source = self.root / 'sources' / 'example'
        self.assertEqual((source / 'APPLE_LICENSE').read_bytes(), b'license')
        (source / 'code.c').write_text('local modification')
        FETCH.fetch('example', entry)
        self.assertEqual((source / 'code.c').read_text(), 'local modification')
        self.assertEqual(json.loads((source / '.commonplace-source.json').read_text()), entry)

    def test_rejects_corrupted_archive(self):
        path, entry = self.archive({'upstream/code.c': b'int x;'})
        path.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            FETCH.fetch('example', entry)
        self.assertFalse((self.root / 'sources' / 'example').exists())

    def test_rejects_path_traversal(self):
        _, entry = self.archive({'../../escape': b'outside'})
        with self.assertRaises(tarfile.FilterError):
            FETCH.fetch('example', entry)
        self.assertFalse((self.root / 'escape').exists())
        self.assertFalse((self.root / 'sources' / 'example').exists())

    def test_refuses_to_replace_unknown_source_tree(self):
        _, entry = self.archive({'upstream/code.c': b'int x;'})
        source = self.root / 'sources' / 'example'
        source.mkdir(parents=True)
        (source / 'keep').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'refusing to replace'):
            FETCH.fetch('example', entry)
        self.assertEqual((source / 'keep').read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
