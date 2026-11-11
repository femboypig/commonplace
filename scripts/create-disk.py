#!/usr/bin/env python3
"""Create the persistent HFS+ data disk once; preserve every existing image."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent.parent
DEFAULT=ROOT/'build/disks/data.hfs'


def validate(path):
    if not path.is_file() or path.stat().st_size < 16*1024*1024 or path.stat().st_size%512:
        raise ValueError('not a supported disk image: '+str(path))
    with path.open('rb') as stream:
        stream.seek(1024)
        if stream.read(2) not in (b'H+',b'HX'):
            raise ValueError('existing image is not HFS+: '+str(path))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path',type=Path,default=DEFAULT)
    parser.add_argument('--size',type=int,default=64,help='size of a new image in MiB')
    options=parser.parse_args()
    path=options.path.resolve()
    if path.exists():
        validate(path)
        print('preserving persistent disk: '+str(path))
        return
    if not 16<=options.size<=1024:
        parser.error('size must be 16..1024 MiB')
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent,prefix='.create-') as temporary:
        image=Path(temporary)/'data.hfs'
        with image.open('wb') as output: output.truncate(options.size*1024*1024)
        subprocess.run([str(ROOT/'toolchain/bin/newfs_hfs'),'-J','-v','commonplace-data',
                        '-U','0','-G','0','-M','755',str(image)],check=True)
        validate(image)
        with image.open('rb') as stream: os.fsync(stream.fileno())
        try: os.link(image,path)
        except FileExistsError: validate(path)
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(directory)
    finally: os.close(directory)
    print('persistent disk ready: '+str(path))


if __name__=='__main__': main()
