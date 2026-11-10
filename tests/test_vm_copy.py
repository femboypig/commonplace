"""Exercise XNU's copy-and-remove path with observable map operations."""

import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VmCopyRemovalTests(unittest.TestCase):
    def test_copy_preserves_removal_flags_for_user_and_kernel_maps(self):
        if not (ROOT / 'sources/xnu/osfmk/vm/vm_map.c').is_file():
            self.skipTest('run make fetch to obtain the pinned XNU source')
        spec = importlib.util.spec_from_file_location('xnu_build', ROOT / 'scripts/build-xnu.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=ROOT / 'build', prefix='test-vm-copy-') as directory:
            directory = Path(directory)
            module.apply_source_patches(directory)
            text = (directory / 'osfmk/vm/vm_map.c').read_text()
            function = re.search(r'static kern_return_t\nvm_map_copyin_kernel_buffer\(.*?\n}\n',
                                 text, re.DOTALL).group()
            header = (ROOT / 'sources/xnu/osfmk/vm/vm_map.h').read_text()
            flags = '\n'.join(re.findall(
                r'^#define\s+VM_MAP_REMOVE_(?:KUNWIRE|INTERRUPTIBLE|WAIT_FOR_KWIRE)\s+[^\n]+',
                header, re.MULTILINE))
            harness = (ROOT / 'tests/vm-copy-probe.c').read_text()
            harness = harness.replace('/* XNU_FLAGS */', flags).replace('/* XNU_COPY */', function)
            (directory / 'probe.c').write_text(harness)
            subprocess.run(['clang', '-std=gnu99', '-Werror=bitwise-conditional-parentheses',
                            str(directory / 'probe.c'), '-o', str(directory / 'probe')], check=True)
            subprocess.run([str(directory / 'probe')], check=True)
