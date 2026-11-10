#!/usr/bin/env python3
"""Create a standalone HFS+ bootstrap root image without mounting it."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'build/rootfs'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    formatter = ROOT / 'toolchain/bin/newfs_hfs'
    hfs = ROOT / 'toolchain/bin/hfsplus'
    init = ROOT / 'build/userland/init'
    for artifact in (formatter, hfs, init):
        if not artifact.is_file():
            raise SystemExit('missing rootfs input: ' + str(artifact))
    with tempfile.TemporaryDirectory(dir=OUT, prefix='.image-') as temporary:
        temporary = Path(temporary)
        image = temporary / 'root.hfs'
        with image.open('wb') as output:
            output.truncate(32 * 1024 * 1024)
        subprocess.run([str(formatter), '-v', 'commonplace', '-U', '0', '-G', '0',
                        '-M', '755', str(image)], check=True)
        for directory in ('dev', 'sbin'):
            subprocess.run([str(hfs), str(image), 'mkdir', '/' + directory], check=True)
        # XNU 15's primordial process searches this path for its first executable.
        subprocess.run([str(hfs), str(image), 'add', str(init), '/sbin/launchd'], check=True)
        subprocess.run([str(hfs), str(image), 'chmod', '755', '/sbin/launchd'], check=True)
        extracted = temporary / 'init'
        subprocess.run([str(hfs), str(image), 'extract', '/sbin/launchd', str(extracted)], check=True)
        if extracted.read_bytes() != init.read_bytes():
            raise ValueError('HFS+ init round-trip verification failed')
        subprocess.run([str(hfs), str(image), 'ls', '/sbin'], check=True)
        image.replace(OUT / 'root.hfs')
    metadata = {'image': 'build/rootfs/root.hfs', 'size': (OUT / 'root.hfs').stat().st_size,
                'sha256': hashlib.sha256((OUT / 'root.hfs').read_bytes()).hexdigest(),
                'init_sha256': hashlib.sha256(init.read_bytes()).hexdigest()}
    (OUT / 'image.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
