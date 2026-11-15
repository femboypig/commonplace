#!/usr/bin/env python3
"""Exercise password recovery, cancellation, interruption and HFS+ crash repair."""

from datetime import datetime, timezone
import hashlib
import json
import re
import shutil
import subprocess
import sys
from rootfs_image import ROOT
from service_image import build_service_image
from guest_console import Console, PROMPT
from qemu_machine import command_for, KERNEL
from offline_image import locked_image
from update_check_support import run_update

ROOT_PASSWORD = "Recovery-root-passphrase-2026!"
USER_PASSWORD = "Recovery-user-passphrase-2026!"
NEW_PASSWORD = "Recovery-changed-passphrase-2026!"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recover_command(image, *options):
    return [
        sys.executable,
        str(ROOT / "scripts/recover-system.py"),
        "--path",
        str(image),
        *options,
    ]


def reset(image, log, user, password=None, *, interrupt=False):
    before = digest(image)
    backups = set(image.parent.glob(image.name + ".previous-*"))
    console = Console(recover_command(image, "--reset-password", user), log)
    try:
        console.expect(rb"New password:", seconds=180)
        if interrupt:
            console.process.terminate()
            if console.process.wait(timeout=15) != 143:
                raise ValueError("recovery did not handle termination")
        else:
            console.sendline(password or "")
            if password:
                console.expect(rb"Retype new password:")
                console.sendline(password)
            console.expect(rb"commonplace: powering off q35", seconds=180)
            if password:
                console.expect(rb"system ready: ", seconds=20)
                if console.process.wait(timeout=10) != 0:
                    raise ValueError("password recovery command failed")
            elif console.process.wait(timeout=15) == 0:
                raise ValueError("cancelled recovery reported success")
    finally:
        console.close()
    if password:
        added = set(image.parent.glob(image.name + ".previous-*")) - backups
        if len(added) != 1 or digest(added.pop()) != before:
            raise ValueError("password reset did not retain an exact backup")
        if password.encode() in log.read_bytes():
            raise ValueError("recovery echoed a password")
    elif (
        digest(image) != before
        or set(image.parent.glob(image.name + ".previous-*")) != backups
    ):
        raise ValueError("aborted recovery changed the original or published a backup")


def boot(image, log):
    return Console(
        command_for([KERNEL], 1024, bounded=False, system_disk=image, disk_root=True)
        + ["-serial", "mon:stdio"],
        log,
    )


def user_session(console, password):
    console.sendline("exit")
    prompt = rb"[A-Za-z0-9.-]+:[^\n]+ tester\$ "
    console.login("tester", password, prompt)
    console.sendline("id -u; cat /home/tester/retained")
    if not re.search(rb"\n501\nretained-user-data\n", console.expect(prompt)):
        raise ValueError("recovery changed user identity or home data")
    console.sendline("exit")
    console.login("root", ROOT_PASSWORD)


def main():
    directory = (
        ROOT
        / "build/recovery-tests"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    directory.mkdir(parents=True)
    image = directory / "system.hfs"
    build_service_image(image, 128)
    reset(image, directory / "cancelled.log", "root")
    reset(image, directory / "interrupted.log", "root", interrupt=True)
    reset(image, directory / "root-reset.log", "root", ROOT_PASSWORD)
    console = boot(image, directory / "provisioned.log")
    try:
        console.login("root", ROOT_PASSWORD)
        console.command(
            "test ! -e /etc/commonplace.setup-required; echo setup-status:$?",
            rb"setup-status:0",
        )
        console.command(
            "cp /etc/master.passwd /tmp/accounts; printf '%s\\n' 'tester:*:501:20::0:0:test user:/home/tester:/bin/sh' >> /tmp/accounts; pwd_mkdb -p /tmp/accounts; mkdir /home /home/tester; chown tester:staff /home/tester; chmod 700 /home/tester",
            rb"pwd_mkdb",
        )
        console.sendline("passwd tester")
        console.change_password(USER_PASSWORD)
        console.expect(PROMPT)
        console.command(
            "echo retained-user-data > /home/tester/retained; chown tester:staff /home/tester/retained",
            rb"\Aecho",
        )
        console.poweroff()
    finally:
        console.close()
    reset(image, directory / "user-reset.log", "tester", NEW_PASSWORD)
    console = boot(image, directory / "user-restored.log")
    try:
        console.login("root", ROOT_PASSWORD)
        user_session(console, NEW_PASSWORD)
        console.poweroff()
    finally:
        console.close()
    clean = directory / "clean.hfs"
    shutil.copyfile(image, clean)
    console = boot(image, directory / "crashed.log")
    try:
        console.login("root", ROOT_PASSWORD)
        console.command(
            "echo committed-before-crash > /root/crash-marker; sync", rb"\Aecho"
        )
        # Terminating QEMU leaves the guest volume mounted with its journal active.
        console.process.terminate()
        console.process.wait(timeout=10)
    finally:
        console.close()
    dirty = digest(image)
    try:
        with locked_image(image):
            raise ValueError("crash fixture was unexpectedly clean")
    except ValueError as error:
        if "not cleanly unmounted" not in str(error):
            raise
    before = set(directory.glob("system.hfs.previous-*"))
    subprocess.run(recover_command(image, "--repair"), check=True)
    added = set(directory.glob("system.hfs.previous-*")) - before
    if len(added) != 1:
        raise ValueError("repair did not publish one recovery snapshot")
    dirty_backup = added.pop()
    if digest(dirty_backup) != dirty:
        raise ValueError("repair changed the original crash snapshot")
    with locked_image(image):
        pass
    console = boot(image, directory / "repaired.log")
    try:
        console.login("root", ROOT_PASSWORD)
        console.command("cat /root/crash-marker", rb"\ncommitted-before-crash\n")
        user_session(console, NEW_PASSWORD)
        console.poweroff()
    finally:
        console.close()
    rollback = directory / "rollback.hfs"
    shutil.copyfile(dirty_backup, rollback)
    run_update(rollback, "--restore", str(clean))
    if digest(rollback) != digest(clean):
        raise ValueError("rollback from an unclean installation changed the source")
    (directory / "summary.json").write_text(
        json.dumps(
            {
                "passed": True,
                "checks": [
                    "cancellation",
                    "termination",
                    "root reset",
                    "user reset",
                    "crash repair",
                    "dirty rollback",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "native password recovery, interruption and crash repair passed: "
        + str(directory)
    )


if __name__ == "__main__":
    main()
