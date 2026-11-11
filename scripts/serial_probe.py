"""Exercise the guest's real TTY through a QEMU serial socket."""
import socket


class SerialProbe:
    cases = (
        (b'help\n', b'\nhelp  pid  echo <text>\n'),
        (b'pid\n', b'\n1\n'),
        (b'echo tty-round-trip-ok\n', b'\ntty-round-trip-ok\n'),
        (b'unknown\n', b'\nunknown command; type help\n'),
        (b'x' * 300 + b'\n', b'\ninput exceeds 255 bytes\n'),
    )

    def __init__(self, path, output):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.connect(str(path))
        self.socket.setblocking(False)
        self.output = output.open('wb')
        self.pending = b''
        self.sent = 0
        self.passed = 0
        self.error = None

    @property
    def done(self):
        return self.error is not None or self.passed == len(self.cases)

    def poll(self):
        while True:
            try:
                data = self.socket.recv(65536)
            except BlockingIOError:
                break
            if not data:
                self.error = 'serial connection closed'
                return
            self.output.write(data)
            self.output.flush()
            self.pending += data.replace(b'\r', b'')
        while b'commonplace> ' in self.pending and not self.done:
            response, self.pending = self.pending.split(b'commonplace> ', 1)
            if self.sent:
                expected = self.cases[self.sent - 1][1]
                if expected not in response:
                    self.error = f'console case {self.sent} returned unexpected output'
                    return
                self.passed += 1
            if not self.done:
                self.socket.sendall(self.cases[self.sent][0])
                self.sent += 1

    def close(self):
        self.socket.close()
        self.output.close()
