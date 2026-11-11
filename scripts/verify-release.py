#!/usr/bin/env python3
"""Verify immutable boot artifacts while leaving the writable data disk alone."""
import hashlib
import json
from pathlib import Path
import sys


def verify(directory):
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest.get('schema')!=1: raise ValueError('unsupported release manifest')
    for name,expected in manifest['immutable'].items():
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts: raise ValueError('invalid artifact path')
        path=directory/relative
        if not path.is_file() or path.is_symlink(): raise ValueError('missing artifact: '+name)
        with path.open('rb') as stream: actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=expected: raise ValueError('artifact checksum mismatch: '+name)
    return manifest


if __name__=='__main__':
    try: verify(Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd())
    except (OSError,ValueError,KeyError) as error: raise SystemExit(str(error))
