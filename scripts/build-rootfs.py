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
    names = json.loads((ROOT / 'build/userland/programs.json').read_text())
    programs = {('/sbin/launchd' if name == 'init' else '/bin/' + name): ROOT / 'build/userland' / name
                for name in names}
    for artifact in (formatter, hfs, *programs.values()):
        if not artifact.is_file():
            raise SystemExit('missing rootfs input: ' + str(artifact))
    with tempfile.TemporaryDirectory(dir=OUT, prefix='.image-') as temporary:
        temporary = Path(temporary)
        image = temporary / 'root.hfs'
        with image.open('wb') as output:
            output.truncate(32 * 1024 * 1024)
        subprocess.run([str(formatter), '-v', 'commonplace', '-U', '0', '-G', '0',
                        '-M', '755', str(image)], check=True)
        for directory in ('dev', 'sbin', 'bin', 'etc', 'tmp', 'root', 'data', 'usr', 'usr/bin', 'usr/sbin'):
            subprocess.run([str(hfs), str(image), 'mkdir', '/' + directory], check=True)
        hashes = {}
        for destination, program in programs.items():
            subprocess.run([str(hfs), str(image), 'add', str(program), destination], check=True)
            subprocess.run([str(hfs), str(image), 'chmod', '755', destination], check=True)
            extracted = temporary / 'verify'
            subprocess.run([str(hfs), str(image), 'extract', destination, str(extracted)], check=True)
            if extracted.read_bytes() != program.read_bytes():
                raise ValueError('HFS+ program round-trip verification failed: ' + destination)
            hashes[destination] = hashlib.sha256(program.read_bytes()).hexdigest()
        for configuration in sorted((ROOT/'userland/darwin/etc').iterdir()):
            destination = '/etc/'+configuration.name
            subprocess.run([str(hfs), str(image), 'add', str(configuration), destination], check=True)
            mode = '600' if configuration.name == 'master.passwd' else '644'
            subprocess.run([str(hfs), str(image), 'chmod', mode, destination], check=True)
            hashes[destination] = hashlib.sha256(configuration.read_bytes()).hexdigest()
        subprocess.run([str(hfs), str(image), 'chmod', '1777', '/tmp'], check=True)
        motd = temporary / 'motd'
        motd.write_text('commonplace\nRAM root is temporary. Use mounted /data for persistent files.\n')
        subprocess.run([str(hfs), str(image), 'add', str(motd), '/etc/motd'], check=True)
        subprocess.run([str(hfs), str(image), 'ls', '/bin'], check=True)
        image.replace(OUT / 'root.hfs')
    metadata = {'image': 'build/rootfs/root.hfs', 'size': (OUT / 'root.hfs').stat().st_size,
                'sha256': hashlib.sha256((OUT / 'root.hfs').read_bytes()).hexdigest(),
                'init_sha256': hashlib.sha256(init.read_bytes()).hexdigest(),
                'programs': hashes}
    (OUT / 'image.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
