#!/usr/bin/env python3
"""Verify rejected and interrupted maintenance leaves installed images intact."""

from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
from rootfs_image import ROOT
from service_image import build_service_image
from guest_console import Console
from qemu_machine import command_for, KERNEL
from update_check_support import run_update


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_preserved(image, before):
    if digest(image) != before or list(image.parent.glob(image.name + ".previous-*")):
        raise ValueError("failed maintenance changed the installed image")


def interrupt_update(image, output):
    before = digest(image)
    with output.open("wb") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "scripts/update-system.py"),
                "--path",
                str(image),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise ValueError(
                        "updater exited before the interruption checkpoint"
                    )
                children = (
                    Path(f"/proc/{process.pid}/task/{process.pid}/children")
                    .read_text()
                    .split()
                )
                for child in children:
                    try:
                        args = Path(f"/proc/{child}/cmdline").read_bytes().split(b"\0")
                    except FileNotFoundError:
                        continue
                    if b"-initrd" not in args:
                        continue
                    recovery = Path(
                        args[args.index(b"-initrd") + 1].decode().split(",")[-1]
                    )
                    serial = recovery.parent / "boot/serial.log"
                    if (
                        serial.is_file()
                        and b"installed:/bin/echo" in serial.read_bytes()
                    ):
                        process.terminate()
                        if process.wait(timeout=15) != 143:
                            raise ValueError("updater did not handle termination")
                        assert_preserved(image, before)
                        if list(image.parent.glob(".update-*")):
                            raise ValueError("interruption left a staging image behind")
                        return
                time.sleep(0.05)
            raise TimeoutError(
                "native update did not reach its interruption checkpoint"
            )
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)


def main():
    directory = (
        ROOT
        / "build/maintenance-failure-checks"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    directory.mkdir(parents=True)
    original = directory / "original.hfs"
    build_service_image(original, 96)
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    for name in ("unknown-profile", "profile-symlink", "interrupted"):
        image = directory / (name + ".hfs")
        shutil.copyfile(original, image)
        if name == "unknown-profile":
            profile = directory / "profile"
            profile.write_text("unsupported-profile\n")
            subprocess.run(
                [
                    hfs,
                    str(image),
                    "add",
                    str(profile),
                    "/usr/share/commonplace/profile",
                ],
                check=True,
            )
        elif name == "profile-symlink":
            subprocess.run(
                [hfs, str(image), "rm", "/usr/share/commonplace/profile"], check=True
            )
            subprocess.run(
                [
                    hfs,
                    str(image),
                    "symlink",
                    "/usr/share/commonplace/profile",
                    "/root/private",
                ],
                check=True,
            )
        else:
            subprocess.run(
                [
                    hfs,
                    str(image),
                    "add",
                    str(ROOT / "build/userland/false"),
                    "/bin/echo",
                ],
                check=True,
            )
        before = digest(image)
        if name == "interrupted":
            interrupt_update(image, directory / "interrupted.log")
        else:
            result = run_update(image, success=False)
            diagnostic = re.search(
                r"^ValueError: native recovery transaction failed; diagnostics: (.+)$",
                result.stderr,
                re.M,
            )
            if not diagnostic:
                raise ValueError(
                    "rejected update did not identify its native diagnostics"
                )
            serial = (Path(diagnostic[1]) / "boot/serial.log").read_text()
            reason = (
                "unsupported installed profile"
                if name == "unknown-profile"
                else "installed profile is a symbolic link"
            )
            if reason not in serial:
                raise ValueError(
                    "update failed for a different reason than the intended guard"
                )
            assert_preserved(image, before)
    active = directory / "active.hfs"
    shutil.copyfile(original, active)
    console = Console(
        command_for([KERNEL], 1024, bounded=False, system_disk=active, disk_root=True)
        + ["-serial", "mon:stdio"],
        directory / "active.log",
    )
    try:
        console.expect(rb"New password:", seconds=180)
        result = run_update(active, success=False)
        if "disk is in use" not in result.stderr:
            raise ValueError("updater did not reject the active QEMU disk")
        if list(directory.glob("active.hfs.previous-*")):
            raise ValueError("updater published a backup for an active disk")
    finally:
        console.close()
    (directory / "summary.json").write_text(
        json.dumps(
            {
                "passed": True,
                "checks": [
                    "unknown profile",
                    "profile symlink",
                    "interruption during replacement",
                    "active QEMU rejection",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "native maintenance rejection and interruption checks passed: " + str(directory)
    )


if __name__ == "__main__":
    main()
