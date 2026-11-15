#!/usr/bin/env python3
"""Repair an offline system or reset a local password through Apple recovery tools."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
from offline_image import image_transaction, locked_image, maintenance_signals
from recovery_session import recovery_image, install_script, run_script, console_for
from guest_console import PROMPT
from rootfs_image import ROOT


def reset_password(directory, recovery, system, user):
    commands = [
        "set -eu",
        "mounted=no",
        """finish() {
    status=$?
    trap - EXIT
    if [ "$mounted" = yes ]; then
        sync
        umount /tmp/system || status=1
    fi
    if [ "$status" = 0 ]; then
        fsck_hfs -fn -c 16m /dev/rcp1 || status=1
    fi
    printf 'password-recovery-status:%s\\n' "$status"
    poweroff
}""",
        "trap finish EXIT",
        "fsck_hfs -fn -c 16m /dev/rcp1",
        "mkdir /tmp/system",
        "mount -t hfs /dev/cp1 /tmp/system",
        "mounted=yes",
        "test ! -L /tmp/system/etc",
        "test -d /tmp/system/etc",
        "passwd -i file -l /tmp/system/etc/master.passwd -- " + shlex.quote(user),
    ]
    install_script(recovery, directory, "password.sh", "\n".join(commands) + "\n")
    print(
        "booting recovery; enter the new password when Apple passwd prompts", flush=True
    )
    console = console_for(directory, recovery, system)
    try:
        console.expect(PROMPT, seconds=180)
        console.sendline("sh /tmp/password.sh")
        console.interact()
    finally:
        console.close()
    serial = (directory / "boot/serial.log").read_text().replace("\r", "")
    if (
        re.findall(r"^password-recovery-status:([0-9]+)$", serial, re.M) != ["0"]
        or "commonplace: powering off q35" not in serial
    ):
        raise ValueError("password recovery did not complete; original disk preserved")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=ROOT / "build/disks/system.hfs")
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument(
        "--repair", action="store_true", help="run Apple's HFS+ repair on a staged copy"
    )
    operation.add_argument(
        "--reset-password",
        metavar="USER",
        help="interactively replace a local password",
    )
    options = parser.parse_args()
    if options.reset_password and not os.isatty(0):
        parser.error("password recovery requires an interactive terminal")
    path = options.path.resolve(strict=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    evidence = ROOT / "build/recovery-checks" / stamp
    evidence.mkdir(parents=True)
    with image_transaction(path, stamp, allow_unclean=options.repair) as transaction:
        recovery = recovery_image(evidence)
        if options.repair:
            install_script(
                recovery,
                evidence,
                "repair.sh",
                "set -eu\nfsck_hfs -fy -c 16m /dev/rcp1\nfsck_hfs -fn -c 16m /dev/rcp1\necho filesystem-repaired\n",
            )
            response = run_script(evidence, recovery, transaction.staged, "repair.sh")
            if "\nfilesystem-repaired\n" not in response:
                raise ValueError("filesystem repair did not complete")
        else:
            reset_password(
                evidence, recovery, transaction.staged, options.reset_password
            )
        with locked_image(transaction.staged):
            pass
    result = {
        "passed": True,
        "image": str(path),
        "backup": str(transaction.backup),
        "operation": "repair" if options.repair else "reset-password",
        "user": options.reset_password,
    }
    (evidence / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("system ready: " + str(path))
    print("previous system: " + str(transaction.backup))
    print("verification: " + str(evidence))


if __name__ == "__main__":
    with maintenance_signals():
        main()
