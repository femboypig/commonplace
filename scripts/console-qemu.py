#!/usr/bin/env python3
"""Attach the terminal to commonplace; use poweroff for a clean exit."""
import argparse
import os
from qemu_machine import ROOT, KERNEL, LOADER, ROOT_IMAGE, DATA_DISK, command_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--memory', type=int, default=1024)
    options = parser.parse_args()
    if not 512 <= options.memory <= 8192:
        parser.error('memory must be 512..8192 MiB')
    for path in (LOADER, KERNEL, ROOT_IMAGE, DATA_DISK):
        if not path.is_file():
            parser.error('missing artifact: ' + str(path))
    os.chdir(ROOT)
    command = command_for([KERNEL.relative_to(ROOT), ROOT_IMAGE.relative_to(ROOT)],
                          options.memory, DATA_DISK.relative_to(ROOT), bounded=False) + ['-serial', 'mon:stdio']
    os.execvp(command[0], command)


if __name__ == '__main__':
    main()
