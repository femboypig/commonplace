"""PTY-backed guest console for interactive QEMU lifecycle checks."""

import errno
import os
import pty
import re
import select
import subprocess
import time

PROMPT = rb"[A-Za-z0-9][A-Za-z0-9.-]{0,254}:/ root# "


class Console:
    def __init__(self, command, output):
        self.master, slave = pty.openpty()
        self.process = subprocess.Popen(
            command,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            start_new_session=True,
        )
        os.close(slave)
        self.log = output.open("wb")
        self.pending = b""

    def expect(self, pattern, seconds=60):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            match = re.search(pattern, self.pending)
            if match:
                response = self.pending[: match.end()]
                self.pending = self.pending[match.end() :]
                return response
            if not select.select(
                [self.master], [], [], max(0, min(0.25, deadline - time.monotonic()))
            )[0]:
                continue
            try:
                data = os.read(self.master, 65536)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                data = b""
            if not data:
                raise RuntimeError(
                    "guest console closed before the expected response"
                )
            self.log.write(data)
            self.log.flush()
            self.pending += data.replace(b"\r", b"")
        raise TimeoutError("guest console timed out: " + repr(self.pending[-512:]))

    def command(self, text, expected):
        os.write(self.master, (text + "\n").encode())
        response = self.expect(PROMPT)
        if not re.search(expected, response):
            raise ValueError(
                "unexpected guest command output: " + repr(response[-512:])
            )

    def poweroff(self):
        os.write(self.master, b"poweroff\n")
        self.expect(rb"commonplace: powering off q35")
        if self.process.wait(timeout=10) != 0:
            raise ValueError("guest QEMU did not exit cleanly")

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
