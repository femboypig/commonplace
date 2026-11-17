"""PTY-backed guest console for interactive QEMU lifecycle checks."""

import errno
import os
import pty
import re
import select
import subprocess
import time
import sys
import termios
import tty

PROMPT = rb"[A-Za-z0-9][A-Za-z0-9.-]{0,254}:[^\n]{1,1024}? root# "


class Console:
    def __init__(self, command, output, *, cwd=None):
        self.master, slave = pty.openpty()
        self.process = subprocess.Popen(
            command,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            start_new_session=True,
            cwd=cwd,
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
                raise RuntimeError("guest console closed before the expected response")
            self.log.write(data)
            self.log.flush()
            self.pending += data.replace(b"\r", b"")
            if re.search(rb"(?:^|\n)panic\(cpu [0-9]+ caller", self.pending):
                raise RuntimeError("guest kernel panic: " + repr(self.pending[-3000:]))
        raise TimeoutError("guest console timed out: " + repr(self.pending[-512:]))

    def sendline(self, text):
        os.write(self.master, (text + "\n").encode())

    def login(self, username, password, prompt=PROMPT, seconds=180):
        self.expect(rb"login: ", seconds=seconds)
        self.sendline(username)
        self.expect(rb"Password:")
        self.sendline(password)
        return self.expect(prompt)

    def change_password(self, password, old=None, *, seconds=60):
        if old is not None:
            self.expect(rb"Old password:", seconds=seconds)
            self.sendline(old)
        self.expect(rb"New password:", seconds=seconds)
        self.sendline(password)
        self.expect(rb"Retype new password:", seconds=seconds)
        self.sendline(password)

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

    def interact(self):
        """Forward a real terminal without logging keyboard input or echoing secrets."""
        terminal = sys.stdin.fileno()
        if not os.isatty(terminal):
            raise ValueError("interactive recovery requires a terminal")
        settings = termios.tcgetattr(terminal)
        try:
            tty.setraw(terminal)
            if self.pending:
                sys.stdout.buffer.write(self.pending)
                sys.stdout.buffer.flush()
                self.pending = b""
            while True:
                ready, _, _ = select.select([self.master, terminal], [], [], 0.25)
                if self.master in ready:
                    try:
                        data = os.read(self.master, 65536)
                    except OSError as error:
                        if error.errno != errno.EIO:
                            raise
                        data = b""
                    if not data:
                        break
                    self.log.write(data)
                    self.log.flush()
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
                if terminal in ready:
                    data = os.read(terminal, 4096)
                    if not data:
                        raise EOFError("recovery terminal closed")
                    offset = 0
                    while offset < len(data):
                        offset += os.write(self.master, data[offset:])
            if self.process.wait(timeout=10) != 0:
                raise ValueError("recovery VM did not exit cleanly")
        finally:
            termios.tcsetattr(terminal, termios.TCSANOW, settings)

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
