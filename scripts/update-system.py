#!/usr/bin/env python3
"""Update an offline system through Darwin recovery, retaining a rollback image."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
from create_disk_image import validate_image, sync_directory
from rootfs_image import ROOT, system_files


@contextmanager
def locked_image(path):
    with path.open("r+b") as stream:
        try:
            fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("disk is in use; shut down its VM first: " + str(path))
        identity = os.fstat(stream.fileno())
        validate_image(path)
        stream.seek(1028)
        attributes = struct.unpack(">I", stream.read(4))[0]
        if not attributes & 0x100:
            raise ValueError("disk was not cleanly unmounted; use recovery first")
        yield identity


def recovery_check(directory, image, update):
    recovery = directory / "recovery.hfs"
    shutil.copyfile(ROOT / "build/rootfs/root.hfs", recovery)
    metadata = json.loads((ROOT / "build/rootfs/image.json").read_text())
    if hashlib.sha256(recovery.read_bytes()).hexdigest() != metadata["sha256"]:
        raise ValueError("recovery image does not match its manifest")
    if update:
        for target, source in system_files().items():
            if hashlib.sha256(source.read_bytes()).hexdigest() != metadata[
                "programs"
            ].get(target):
                raise ValueError(
                    "rebuild the recovery image before updating: " + target
                )
    script = directory / "update.sh"
    commands = ["set -eu", "fsck_hfs -fn -c 16m /dev/rcp1"]
    if update:
        commands += ["mkdir /tmp/system", "mount -t hfs /dev/cp1 /tmp/system"]
        for path in ("/bin", "/sbin", "/usr", "/usr/lib", "/usr/lib/system"):
            target = shlex.quote("/tmp/system" + path)
            commands.append(f"test -d {target} && test ! -L {target}")
        for path in ("/var", "/var/log", "/var/run"):
            target = shlex.quote("/tmp/system" + path)
            commands += [f"test ! -L {target}", f"mkdir -p {target}"]
        for path in system_files():
            source, target = shlex.quote(path), shlex.quote("/tmp/system" + path)
            commands += [
                f"test ! -L {target}",
                f"test ! -e {target} || test -f {target}",
                f"cp -p {source} {target}",
                f'test "$(cksum < {source})" = "$(cksum < {target})"',
            ]
        commands += ["sync", "umount /tmp/system", "fsck_hfs -fn -c 16m /dev/rcp1"]
    commands.append("echo system-image-verified")
    script.write_text("\n".join(commands) + "\n")
    subprocess.run(
        [
            str(ROOT / "toolchain/bin/hfsplus"),
            str(recovery),
            "add",
            str(script),
            "/tmp/update.sh",
        ],
        check=True,
    )
    cases = directory / "cases.json"
    cases.write_text(
        json.dumps(
            [
                {
                    "name": "offline system transaction",
                    "send": "sh /tmp/update.sh; echo update-status:$?\n",
                    "expect": r"\nsystem-image-verified\nupdate-status:0\n",
                }
            ]
        )
        + "\n"
    )
    with (directory / "boot.log").open("w") as log:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/boot-qemu.py"),
                "--seconds",
                "600",
                "--memory",
                "1024",
                "--root-image",
                str(recovery),
                "--system-disk",
                str(image),
                "--check-console",
                "--console-case-file",
                str(cases),
                "--expect-shutdown",
                "poweroff",
                "--output",
                str(directory / "boot"),
            ],
            check=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=ROOT / "build/disks/system.hfs")
    parser.add_argument(
        "--restore", type=Path, help="restore a previous full system image"
    )
    options = parser.parse_args()
    path = options.path.resolve(strict=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    evidence = ROOT / "build/update-checks" / stamp
    evidence.mkdir(parents=True)
    # The stable lock also serializes updates across atomic inode replacement.
    with path.with_name(path.name + ".update.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with locked_image(path) as identity:
            source = options.restore.resolve(strict=True) if options.restore else path
            if options.restore and source == path:
                raise ValueError("rollback source must be a different image")
            with tempfile.TemporaryDirectory(
                dir=path.parent, prefix=".update-"
            ) as temporary:
                staged = Path(temporary) / "system.hfs"
                if options.restore:
                    with locked_image(source):
                        shutil.copyfile(source, staged)
                else:
                    shutil.copyfile(source, staged)
                recovery_check(evidence, staged, update=not options.restore)
                current = path.stat()
                if (current.st_dev, current.st_ino) != (
                    identity.st_dev,
                    identity.st_ino,
                ):
                    raise ValueError("system image changed during the update")
                backup = path.with_name(path.name + ".previous-" + stamp)
                shutil.copystat(path, staged)
                with staged.open("rb") as stream:
                    os.fsync(stream.fileno())
                os.link(path, backup)
                sync_directory(path.parent)
                os.replace(staged, path)
                sync_directory(path.parent)
    (evidence / "result.json").write_text(
        json.dumps(
            {
                "passed": True,
                "image": str(path),
                "backup": str(backup),
                "restored_from": str(source) if options.restore else None,
            },
            indent=2,
        )
        + "\n"
    )
    print("system ready: " + str(path))
    print("previous system: " + str(backup))
    print("verification: " + str(evidence))


if __name__ == "__main__":
    main()
