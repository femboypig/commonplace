#!/usr/bin/env python3
"""Package a ready-to-run QEMU system with a new, empty persistent disk."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parent.parent


def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    subprocess.run(['python3',str(ROOT/'scripts/check-kernel.py')],check=True)
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise SystemExit('commit the source changes before packaging a release')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    name='commonplace-qemu-x86_64-'+revision[:12]
    output=ROOT/'build/releases'
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output,prefix='.package-') as temporary:
        staging=Path(temporary)/name
        staging.mkdir()
        files={
            'build/boot/loader.elf':'build/boot/loader.elf',
            'build/xnu/obj/DEVELOPMENT_X86_64/kernel.development':'build/xnu/obj/DEVELOPMENT_X86_64/kernel.development',
            'build/rootfs/root.hfs':'build/rootfs/root.hfs',
            'scripts/console-qemu.py':'scripts/console-qemu.py',
            'scripts/qemu_machine.py':'scripts/qemu_machine.py',
            'scripts/verify-release.py':'scripts/verify-release.py',
            'run.sh':'scripts/run-release.sh',
            'sources.lock.json':'sources.lock.json',
            'licenses/APPLE_LICENSE':'sources/xnu/APPLE_LICENSE',
            'licenses/openssl.txt':'sources/openssl/LICENSE.txt',
            'licenses/compiler-rt.txt':'sources/compiler_rt/LICENSE.TXT',
        }
        for destination,source in files.items():
            target=staging/destination
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/source,target)
        (staging/'run.sh').chmod(0o755)
        disk=staging/'build/disks/data.hfs'
        subprocess.run(['python3',str(ROOT/'scripts/create-disk.py'),'--path',str(disk)],check=True)
        manifest={'schema':1,'target':'qemu-q35-x86_64-kvm','revision':revision,
                  'immutable':{name:digest(staging/name) for name in files},
                  'mutable':{'build/disks/data.hfs':{'initial_sha256':digest(disk),'size':disk.stat().st_size}}}
        (staging/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        archive=Path(temporary)/(name+'.tar.gz')
        with tarfile.open(archive,'w:gz') as bundle:
            bundle.add(staging,arcname=name)
        archive.replace(output/archive.name)
    print(output/(name+'.tar.gz'))


if __name__=='__main__': main()
