"""Exercise bounded shell syntax independently of the Darwin syscall runtime."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent


class ShellParserTest(unittest.TestCase):
    def test_syntax_boundaries_and_fuzz(self):
        with tempfile.TemporaryDirectory(prefix='commonplace-shell-') as temporary:
            output=Path(temporary)/'probe'
            subprocess.run(['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror',
                            '-fsanitize=address,undefined','-fno-omit-frame-pointer',
                            '-I'+str(ROOT/'userland/include'),'-I'+str(ROOT/'userland/sh'),
                            str(ROOT/'tests/shell-parser-probe.c'),
                            str(ROOT/'userland/sh/lexer.c'),str(ROOT/'userland/sh/parser.c'),
                            '-o',str(output)],check=True)
            subprocess.run([str(output)],check=True)
