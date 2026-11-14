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
