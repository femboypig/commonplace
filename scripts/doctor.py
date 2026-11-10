#!/usr/bin/env python3
"""Report host requirements without installing or changing system packages."""

import fcntl
from pathlib import Path
import platform
import shutil
import sys

REQUIRED = (
    'clang', 'clang++', 'make', 'bison', 'flex', 'autoreconf', 'libtoolize',
    'curl', 'python3', 'unifdef', 'qemu-system-x86_64', 'qemu-img', 'mformat',
    'mcopy', 'cpio', 'patch', 'llvm-readobj',
)


def main():
    missing = []
    print(f'host: {platform.system()} {platform.machine()}')
    if (platform.system(), platform.machine()) != ('Linux', 'x86_64'):
        print('error: the initial build host must be x86_64 Linux')
        return 1
    for tool in REQUIRED:
        path = shutil.which(tool)
        print(f'{tool}: {path or "missing"}')
        if not path:
            missing.append(tool)
    firmware = list(Path('/usr/share/edk2-ovmf').rglob('OVMF_CODE*.fd'))
    print('ovmf: ' + (', '.join(str(p) for p in firmware) or 'missing'))
    if not firmware:
        missing.append('ovmf firmware')
    try:
        with open('/dev/kvm', 'rb+', buffering=0) as kvm:
            version = fcntl.ioctl(kvm, 0xAE00, 0)
            if version != 12:
                raise OSError(f'unsupported KVM API version {version}')
            import os
            vm = fcntl.ioctl(kvm, 0xAE01, 0)
            os.close(vm)
        print('kvm: vm creation passed')
    except OSError as error:
        print(f'kvm: unavailable ({error}); tcg remains possible')
    free = shutil.disk_usage(Path(__file__).resolve().parent.parent).free
    print(f'workspace free: {free / 1024**3:.1f} GiB')
    if missing:
        print('missing requirements: ' + ', '.join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
