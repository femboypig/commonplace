#!/usr/bin/env python3
"""Attach the terminal to commonplace; use poweroff for a clean exit."""

import argparse
import os
from qemu_machine import (
    ROOT,
    KERNEL,
    LOADER,
    ROOT_IMAGE,
    DATA_DISK,
    SYSTEM_DISK,
    command_for,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory", type=int, default=1024)
    parser.add_argument(
        "--recovery", action="store_true", help="boot the RAM recovery root"
    )
    options = parser.parse_args()
    if not 512 <= options.memory <= 8192:
        parser.error("memory must be 512..8192 MiB")
    required = (
        LOADER,
        KERNEL,
        DATA_DISK,
        ROOT_IMAGE if options.recovery else SYSTEM_DISK,
    )
    for path in required:
        if not path.is_file():
            parser.error("missing artifact: " + str(path))
    os.chdir(ROOT)
    modules = [KERNEL.relative_to(ROOT)]
    if options.recovery:
        modules.append(ROOT_IMAGE.relative_to(ROOT))
    command = command_for(
        modules,
        options.memory,
        DATA_DISK.relative_to(ROOT),
        bounded=False,
        system_disk=SYSTEM_DISK.relative_to(ROOT) if SYSTEM_DISK.is_file() else None,
        disk_root=not options.recovery,
    ) + ["-serial", "mon:stdio"]
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
