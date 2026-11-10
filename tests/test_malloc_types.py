"""Check allocation-name indices against the actual BSD allocation type ABI."""

import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class MallocTypesTest(unittest.TestCase):
    def test_names_match_the_zone_table_and_type_indices(self):
        header = ROOT / 'sources/xnu/bsd/sys/malloc.h'
        if not header.is_file():
            self.skipTest('run make fetch first')
        spec = importlib.util.spec_from_file_location('xnu_build', ROOT / 'scripts/build-xnu.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix='commonplace-malloc-test-') as directory:
            directory = Path(directory)
            module.apply_source_patches(directory)
            original = (directory / 'bsd/kern/kern_malloc.c').read_text()
            names = re.search(r'const char \*memname\[\] = \{.*?\n\};', original, re.S).group(0)
            defines = re.findall(r'^#define\s+(M_(?:LAST|FD_VN_DATA|FD_DIRBUF|NETAGENT))\s+(\d+)',
                                 header.read_text(), re.M)
            self.assertEqual(len(defines), 4)
            probe = directory / 'probe.c'
            probe.write_text('#include <assert.h>\n#include <string.h>\n' +
                             ''.join(f'#define {name} {value}\n' for name, value in defines) +
                             names + '\n' + '''\
_Static_assert(sizeof(memname) / sizeof(memname[0]) == M_LAST, "allocation table size");
int main(void) {
    assert(!strcmp(memname[M_FD_VN_DATA], "fdvnodedata"));
    assert(!strcmp(memname[M_FD_DIRBUF], "fddirbuf"));
    assert(!strcmp(memname[M_NETAGENT], "netagent"));
    return 0;
}
''')
            for enabled in (0, 1):
                flags = [f'-D{feature}={enabled}' for feature in
                         ('NFSCLIENT', 'NFSSERVER', 'TRAFFIC_MGT', 'HFS_COMPRESSION',
                          'FLOW_DIVERT', 'NECP')]
                executable = directory / 'probe'
                subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', *flags,
                                str(probe), '-o', str(executable)], check=True)
                subprocess.run([str(executable)], check=True)
