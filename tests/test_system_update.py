"""An updater must refuse active or unclean images without changing their bytes."""

import importlib.util
import os
from pathlib import Path
import fcntl
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "system_update", ROOT / "scripts/update-system.py"
)
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class UpdateLockTest(unittest.TestCase):
    def test_unclean_volume_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "disk.hfs"
            with image.open("wb") as stream:
                stream.truncate(16 * 1024 * 1024)
                stream.seek(1024)
                stream.write(b"H+\0\4" + struct.pack(">I", 0x2000))
            before = image.read_bytes()
            with self.assertRaisesRegex(ValueError, "not cleanly unmounted"):
                with update.locked_image(image):
                    self.fail("dirty image was accepted")
            self.assertEqual(image.read_bytes(), before)

    def test_qemu_style_byte_range_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "disk.hfs"
            image.write_bytes(b"unchanged")
            with image.open("r+b") as stream:
                fcntl.lockf(stream, fcntl.LOCK_SH, 1, 100)
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; import runpy; "
                        "m=runpy.run_path('scripts/update-system.py'); "
                        "m['locked_image'](Path(__import__('sys').argv[1])).__enter__()",
                        str(image),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    env={
                        **os.environ,
                        "PYTHONPATH": str(ROOT / "scripts"),
                    },
                )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("disk is in use", result.stderr)
            self.assertEqual(image.read_bytes(), b"unchanged")


class ImageTransactionTest(unittest.TestCase):
    def image(self, path, *, clean=True):
        with path.open("wb") as stream:
            stream.truncate(16 * 1024 * 1024)
            stream.seek(1024)
            stream.write(b"H+\0\4" + struct.pack(">I", 0x100 if clean else 0))

    def test_failed_operation_does_not_publish(self):
        from offline_image import image_transaction

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "system.hfs"
            self.image(path)
            before = path.read_bytes()
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                with image_transaction(path, "failed") as transaction:
                    with transaction.staged.open("r+b") as stream:
                        stream.seek(4096)
                        stream.write(b"incomplete update")
                    raise RuntimeError("interrupted")
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(list(path.parent.glob("system.hfs.previous-*")))
            self.assertFalse(list(path.parent.glob(".update-*")))

    def test_restore_accepts_dirty_target_and_preserves_it(self):
        from offline_image import image_transaction

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "system.hfs"
            source = Path(temporary) / "clean.hfs"
            self.image(path, clean=False)
            self.image(source)
            dirty, clean = path.read_bytes(), source.read_bytes()
            with image_transaction(path, "restored", restore=source) as transaction:
                self.assertEqual(transaction.staged.read_bytes(), clean)
            self.assertEqual(path.read_bytes(), clean)
            self.assertEqual(transaction.backup.read_bytes(), dirty)

    def test_restore_rejects_an_alias_of_the_installed_image(self):
        from offline_image import image_transaction

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "system.hfs"
            source = Path(temporary) / "alias.hfs"
            self.image(path)
            os.link(path, source)
            with self.assertRaisesRegex(ValueError, "different image"):
                with image_transaction(path, "alias", restore=source):
                    self.fail("same-inode restore was accepted")

    def test_image_lock_survives_validation_and_staging(self):
        from offline_image import image_transaction

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "system.hfs"
            self.image(path)
            with image_transaction(path, "locked"):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "import fcntl,sys; "
                        "f=open(sys.argv[1], 'r+b'); "
                        "fcntl.lockf(f, fcntl.LOCK_SH | fcntl.LOCK_NB, 1, 100)",
                        str(path),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("BlockingIOError", result.stderr)

    def test_external_changes_are_not_replaced_by_the_staged_copy(self):
        from offline_image import image_transaction

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "system.hfs"
            self.image(path)
            with self.assertRaisesRegex(ValueError, "changed during maintenance"):
                with image_transaction(path, "changed"):
                    subprocess.run(
                        [
                            sys.executable,
                            "-c",
                            "import sys; "
                            "f=open(sys.argv[1], 'r+b'); f.seek(4096); "
                            "f.write(b'external change'); f.close()",
                            str(path),
                        ],
                        check=True,
                    )
            with path.open("rb") as file:
                file.seek(4096)
                self.assertEqual(file.read(15), b"external change")
            self.assertFalse(list(path.parent.glob("system.hfs.previous-*")))
