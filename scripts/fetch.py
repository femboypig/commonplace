#!/usr/bin/env python3
"""Fetch immutable upstream archives without executing upstream scripts."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(name, entry):
    cache = ROOT / '.cache' / 'archives'
    sources = ROOT / 'sources'
    cache.mkdir(parents=True, exist_ok=True)
    sources.mkdir(exist_ok=True)
    archive = cache / (entry['sha256'] + '.tar.gz')
    if not archive.exists():
        with tempfile.NamedTemporaryFile(dir=cache, suffix='.part') as partial:
            subprocess.run([
                'curl', '--fail', '--location', '--silent', '--show-error',
                '--retry', '3', '--connect-timeout', '15', '--max-time', '600',
                '--output', partial.name, entry['url'],
            ], check=True)
            if digest(Path(partial.name)) != entry['sha256']:
                raise ValueError(f'{name}: archive checksum mismatch')
            shutil.copyfile(partial.name, archive)
    if digest(archive) != entry['sha256']:
        raise ValueError(f'{name}: cached archive checksum mismatch: {archive}')

    destination = sources / name
    stamp = destination / '.commonplace-source.json'
    if destination.exists():
        if stamp.exists() and json.loads(stamp.read_text()) == entry:
            print(f'{name}: verified archive; source already present', flush=True)
            return
        raise ValueError(f'{name}: refusing to replace an unrecognized source tree')

    with tempfile.TemporaryDirectory(dir=sources, prefix='.extract-') as temporary:
        temporary = Path(temporary)
        with tarfile.open(archive, 'r:gz') as bundle:
            # Keep upstream licenses, but omit Markdown documentation as requested.
            members = [m for m in bundle.getmembers()
                       if not m.name.lower().endswith(('.md', '.markdown'))]
            bundle.extractall(temporary, members=members, filter='data')
        children = list(temporary.iterdir())
        if len(children) != 1 or not children[0].is_dir():
            raise ValueError(f'{name}: expected a single archive root')
        (children[0] / stamp.name).write_text(json.dumps(entry, indent=2) + '\n')
        children[0].rename(destination)
    print(f'{name}: extracted {entry["revision"]}', flush=True)


def main():
    lock = json.loads((ROOT / 'sources.lock.json').read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('names', nargs='*', help='source names; defaults to all')
    args = parser.parse_args()
    names = args.names or list(lock['sources'])
    unknown = set(names) - lock['sources'].keys()
    if unknown:
        parser.error('unknown sources: ' + ', '.join(sorted(unknown)))
    for name in names:
        fetch(name, lock['sources'][name])


if __name__ == '__main__':
    main()
