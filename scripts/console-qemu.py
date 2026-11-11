#!/usr/bin/env python3
"""Attach the current terminal to the bootstrap console; Ctrl-A X exits QEMU."""
import argparse
import os
from qemu_machine import KERNEL, LOADER, ROOT_IMAGE, command_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--memory', type=int, default=1024)
    options = parser.parse_args()
    if not 512 <= options.memory <= 8192:
        parser.error('memory must be 512..8192 MiB')
    for path in (LOADER, KERNEL, ROOT_IMAGE):
        if not path.is_file():
            parser.error('missing artifact: ' + str(path))
    command = command_for([KERNEL, ROOT_IMAGE], options.memory) + ['-serial', 'mon:stdio']
    os.execvp(command[0], command)


if __name__ == '__main__':
    main()
