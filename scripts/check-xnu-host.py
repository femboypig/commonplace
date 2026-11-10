#!/usr/bin/env python3
"""Check real header exports and Linux host installfile behavior."""

from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
OBJECTS = ROOT / 'build' / 'xnu' / 'obj'


def main():
    exported = OBJECTS / 'EXPORT_HDRS'
    version = (exported / 'libkern/libkern/version.h').read_text()
    if '#define OSRELEASE\t"15.6.0"' not in version:
        raise RuntimeError('missing or incorrect Darwin version header')
    for path in ('osfmk/mach/message.h', 'osfmk/mach/machine/vm_types.h',
                 'bsd/sys/syscall.h', 'iokit/IOKit/IOLib.h',
                 'libkern/libkern/section_keywords.h'):
        if not (exported / path).is_file():
            raise RuntimeError(f'missing exported header: {path}')
    events = (OBJECTS / 'DEVELOPMENT_X86_64/bsd/sys/kdebugevents.h').read_text()
    if 'kd_event_t kd_events[] = {' not in events or '###' in version:
        raise RuntimeError('kernel header generation did not finish')
    print('xnu: Darwin 15.6.0 header exports passed')

    installer = OBJECTS / 'SETUP/installfile/installfile'
    with tempfile.TemporaryDirectory(dir=ROOT / 'build', prefix='check-install-') as temp:
        temp = Path(temp)
        source, destination = temp / 'source', temp / 'destination'
        payload = bytes(range(256)) * 1024
        source.write_bytes(payload)
        destination.write_text('previous content')
        subprocess.run([str(installer), '-c', '-S', '-m', '0444', str(source),
                        str(destination)], check=True)
        if destination.read_bytes() != payload or destination.stat().st_mode & 0o777 != 0o444:
            raise RuntimeError('installfile lost data or installed an incorrect mode')
        (temp / 'link').symlink_to(source)
        failure = subprocess.run([str(installer), str(temp / 'link'), str(destination)],
                                 capture_output=True)
        if failure.returncode == 0 or destination.read_bytes() != payload:
            raise RuntimeError('installfile accepted a symlink or changed the destination on failure')
    print('xnu: multi-buffer atomic installation and symlink rejection passed')


if __name__ == '__main__':
    main()
