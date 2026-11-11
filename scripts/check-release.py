#!/usr/bin/env python3
"""Boot the packaged system, then verify a warm reboot and cold persistence."""
import argparse
from datetime import datetime, timezone
import errno
import json
import os
from pathlib import Path
import pty
import re
import select
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parent.parent
PROMPT = rb'commonplace:/ root# '


class Console:
    def __init__(self, directory, memory, output):
        self.master, slave = pty.openpty()
        self.process = subprocess.Popen([str(directory / 'run.sh'), '--memory', str(memory)],
                                        stdin=slave, stdout=slave, stderr=slave,
                                        start_new_session=True)
        os.close(slave)
        self.log = output.open('wb')
        self.pending = b''

    def expect(self, pattern, seconds=60):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            match = re.search(pattern, self.pending)
            if match:
                response = self.pending[:match.end()]
                self.pending = self.pending[match.end():]
                return response
            if not select.select([self.master], [], [], max(0, min(0.25, deadline-time.monotonic())))[0]:
                continue
            try:
                data = os.read(self.master, 65536)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                data = b''
            if not data:
                raise RuntimeError('packaged console closed before the expected response')
            self.log.write(data)
            self.log.flush()
            self.pending += data.replace(b'\r', b'')
        raise TimeoutError('packaged console timed out: ' + repr(self.pending[-512:]))

    def command(self, text, expected):
        os.write(self.master, (text + '\n').encode())
        response = self.expect(PROMPT)
        if not re.search(expected, response):
            raise ValueError('unexpected packaged command output: ' + repr(response[-512:]))

    def poweroff(self):
        os.write(self.master, b'poweroff\n')
        self.expect(rb'commonplace: powering off q35')
        if self.process.wait(timeout=10) != 0:
            raise ValueError('packaged QEMU did not exit cleanly')

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        os.close(self.master)
        self.log.close()


def boot(directory, memory, output, prepare=False):
    console = Console(directory, memory, output)
    try:
        started = time.monotonic()
        console.expect(PROMPT)
        duration = round(time.monotonic() - started, 3)
        if prepare:
            console.command('ls /data', rb'\Als /data\ncommonplace:/ root# ')
            console.command('echo release-ok > /data/probe', rb'\Aecho release-ok > /data/probe\n')
            console.command('cp /bin/pid /data/program', rb'\Acp /bin/pid /data/program\n')
            os.write(console.master, b'reboot\n')
            console.expect(rb'commonplace: restarting q35')
            console.expect(PROMPT)
        console.command('cat /data/probe', rb'\nrelease-ok\n')
        console.command('/data/program', rb'\n[1-9][0-9]*\n')
        console.poweroff()
        return {'memory_mib': memory, 'prompt_seconds': duration, 'exit': console.process.returncode}
    finally:
        console.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    options = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = ROOT / 'build/release-checks' / stamp
    extracted = output / 'path with spaces'
    extracted.mkdir(parents=True)
    with tarfile.open(options.archive) as archive:
        archive.extractall(extracted, filter='data')
    directories = list(extracted.iterdir())
    if len(directories) != 1 or not directories[0].is_dir():
        raise ValueError('unexpected release layout')
    directory = directories[0]
    subprocess.run(['python3', str(directory/'scripts/verify-release.py'), str(directory)], check=True)
    results = [boot(directory, 512, output/'warm.log', prepare=True),
               boot(directory, 2048, output/'cold.log')]
    subprocess.run(['python3', str(directory/'scripts/verify-release.py'), str(directory)], check=True)
    manifest = json.loads((directory/'manifest.json').read_text())
    summary = {'passed': True, 'revision': manifest['revision'], 'boots': results}
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print('packaged warm reboot and cold persistence passed; evidence: '+str(output))


if __name__ == '__main__':
    main()
