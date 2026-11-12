"""Validate root selection before the loader builds Darwin boot arguments."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class BootOptionsTest(unittest.TestCase):
    def test_bounded_root_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / "probe"
            subprocess.run(
                [
                    "gcc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-fsanitize=address,undefined",
                    "-I" + str(ROOT / "boot"),
                    str(ROOT / "tests/boot-options-probe.c"),
                    str(ROOT / "boot/options.c"),
                    "-o",
                    str(probe),
                ],
                check=True,
            )
            subprocess.run([str(probe)], check=True)
