"""Small synchronous QMP client for bounded boot diagnostics."""

import json
import socket
import time


class Monitor:
    def __init__(self, path, process, timeout=5):
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.settimeout(timeout)
        deadline = time.monotonic() + timeout
        while True:
            try:
                self.socket.connect(str(path))
                break
            except (FileNotFoundError, ConnectionRefusedError):
                if process.poll() is not None or time.monotonic() >= deadline:
                    self.socket.close()
                    raise RuntimeError('QEMU monitor did not become available')
                time.sleep(0.05)
        self.stream = self.socket.makefile('rwb', buffering=0)
        if 'QMP' not in self._read():
            raise RuntimeError('invalid QMP greeting')
        self.command('qmp_capabilities')

    def _read(self):
        line = self.stream.readline()
        if not line:
            raise RuntimeError('QEMU closed the monitor')
        return json.loads(line)

    def command(self, command, **arguments):
        self.stream.write((json.dumps({'execute': command, 'arguments': arguments}) + '\n').encode())
        while True:
            result = self._read()
            if 'error' in result:
                raise RuntimeError(result['error'])
            if 'return' in result:
                return result['return']

    def inspect(self, command):
        return self.command('human-monitor-command', **{'command-line': command})

    def close(self):
        self.stream.close()
        self.socket.close()
