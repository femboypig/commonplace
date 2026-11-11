"""Exercise processes, filesystem operations and shell recovery over the real TTY."""
import re
import socket
import time


class SerialProbe:
    prompt = re.compile(rb'commonplace:[^\n]{1,1024}? root# ')
    cases = (
        ('help', b'help\n', rb'\nbuiltins: cd exit help pid\n'),
        ('shell pid', b'pid\n', rb'\n(?:[2-9]|[1-9][0-9]+)\n'),
        ('external pid', b'/bin/pid\n', rb'\n(?:[3-9]|[1-9][0-9]+)\n'),
        ('kernel identity', b'uname -a\n', rb'\nDarwin commonplace 15\.6\.0 x86_64\n'),
        ('calendar', b'date\n', rb'\n20[0-9]{2}-[01][0-9]-[0-3][0-9] [0-2][0-9]:[0-5][0-9]:[0-5][0-9] UTC\n'),
        ('root directory', b'pwd\n', rb'\n/\n'),
        ('list programs', b'ls /bin\n', rb'\nsh\n'),
        ('quoted arguments', b'echo "two words" \'single quoted\' escaped\\ space\n', rb'\ntwo words single quoted escaped space\n'),
        ('literal dollar', b'echo \'$?\' \\$?\n', rb'\n\$\? \$\?\n'),
        ('create directory', b'mkdir /tmp/check\n', rb'\Amkdir /tmp/check\n\Z'),
        ('change directory', b'cd /tmp/check\n', rb'\Acd /tmp/check\n\Z'),
        ('working directory', b'pwd\n', rb'\n/tmp/check\n'),
        ('write file', b'echo first > data\n', rb'\Aecho first > data\n\Z'),
        ('append file', b'echo second >> data\n', rb'\Aecho second >> data\n\Z'),
        ('read redirection', b'cat < data\n', rb'\nfirst\nsecond\n'),
        ('count words', b'wc -w data\n', rb'\n2\n'),
        ('pipeline', b'echo pipeline-ok | cat | cat\n', rb'\npipeline-ok\n'),
        ('pipe pressure', b'seq 1 5000 | cat | wc -l\n', rb'\n5000\n'),
        ('builtin redirection', b'pwd > place\n', rb'\Apwd > place\n\Z'),
        ('read saved directory', b'cat place\n', rb'\n/tmp/check\n'),
        ('script without newline', b'echo -n \'echo script-ok\' > /tmp/script\n', rb'\Aecho -n \'echo script-ok\' > /tmp/script\n\Z'),
        ('run script', b'sh /tmp/script\n', rb'\nscript-ok\n'),
        ('interrupt child', b'sleep 30\n', rb'sleep 30'),
        ('signal exit status', b'echo $?\n', rb'\n130\n'),
        ('exit status', b'sh -c \'exit 7\'\n', rb'\Ash -c \'exit 7\'\n\Z'),
        ('status expansion', b'echo $?\n', rb'\n7\n'),
        ('pipeline failure', b'true | false\n', rb'\Atrue \| false\n\Z'),
        ('pipeline status', b'echo $?\n', rb'\n1\n'),
        ('missing program', b'not-a-command\n', rb'no such file or directory'),
        ('exec error status', b'echo $?\n', rb'\n127\n'),
        ('syntax error', b'echo "unfinished\n', rb'sh: unclosed quote'),
        ('parser recovery', b'echo parser-recovered\n', rb'\nparser-recovered\n'),
        ('remove files', b'rm data place /tmp/script\n', rb'\Arm data place /tmp/script\n\Z'),
        ('return to root', b'cd /\n', rb'\Acd /\n\Z'),
        ('remove directory', b'rmdir /tmp/check\n', rb'\Armdir /tmp/check\n\Z'),
        ('keep file for restart', b'echo retained > /tmp/retained\n', rb'\Aecho retained > /tmp/retained\n\Z'),
        ('eof supervision', b'\x04', rb'commonplace init: shell exited; restarting'),
        ('restarted shell', b'echo console-recovered\n', rb'\nconsole-recovered\n'),
        ('file after eof', b'cat /tmp/retained\n', rb'\nretained\n'),
        ('exit supervision', b'exit\n', rb'commonplace init: shell exited; restarting'),
        ('file after exit', b'cat /tmp/retained\n', rb'\nretained\n'),
        ('remove restart file', b'rm /tmp/retained\n', rb'\Arm /tmp/retained\n\Z'),
        ('second restart', b'echo shell-ready\n', rb'\nshell-ready\n'),
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
        self.interrupt_at = None

    @property
    def done(self):
        return self.error is not None or self.passed == len(self.cases)

    def poll(self):
        if self.interrupt_at is not None and time.monotonic() >= self.interrupt_at:
            self.socket.sendall(b'\x03')
            self.interrupt_at = None
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
        while not self.done:
            match = self.prompt.search(self.pending)
            if not match:
                return
            response, self.pending = self.pending[:match.start()], self.pending[match.end():]
            if self.sent:
                name, _, expected = self.cases[self.sent - 1]
                if not re.search(expected, response):
                    self.error = f'{name}: unexpected output: {response[-512:]!r}'
                    return
                self.passed += 1
            if not self.done:
                self.socket.sendall(self.cases[self.sent][1])
                if self.cases[self.sent][0] == 'interrupt child':
                    self.interrupt_at = time.monotonic() + 0.5
                self.sent += 1

    def close(self):
        self.socket.close()
        self.output.close()
