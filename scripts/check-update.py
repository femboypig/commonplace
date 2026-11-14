#!/usr/bin/env python3
"""Verify offline updates, preserved configuration, rollback and lock rejection."""

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import subprocess
import shutil
import sys
from rootfs_image import ROOT, build_image


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_update(system, *options, success=True):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/update-system.py"),
            "--path",
            str(system),
            *options,
        ],
        capture_output=True,
        text=True,
    )
    if (result.returncode == 0) != success:
        raise ValueError(result.stdout + result.stderr)
    return result


def boot(directory, system, cases):
    directory.mkdir()
    scenario = directory / "cases.json"
    scenario.write_text(json.dumps(cases) + "\n")
    with (directory / "output.log").open("w") as log:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/boot-qemu.py"),
                "--system-disk",
                str(system),
                "--disk-root",
                "--seconds",
                "180",
                "--check-console",
                "--console-case-file",
                str(scenario),
                "--expect-shutdown",
                "poweroff",
                "--output",
                str(directory),
            ],
            check=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )


def case(name, command, expected):
    return {"name": name, "send": command + "\n", "expect": expected}


def reject_symlink(directory, original):
    image = directory / "rejected.hfs"
    shutil.copyfile(original, image)
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run([hfs, str(image), "rm", "/bin/echo"], check=True)
    subprocess.run(
        [hfs, str(image), "symlink", "/bin/echo", "/root/private-file"], check=True
    )
    before = digest(image)
    run_update(image, success=False)
    if digest(image) != before or list(directory.glob("rejected.hfs.previous-*")):
        raise ValueError("failed update changed the original or published a backup")


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = ROOT / "build/update-tests" / stamp
    directory.mkdir(parents=True)
    system = directory / "system.hfs"
    build_image(system, size_mib=64, persistent=True)
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run([hfs, str(system), "rm", "/sbin/fsck_hfs"], check=True)
    subprocess.run(
        [hfs, str(system), "add", str(ROOT / "build/userland/false"), "/bin/echo"],
        check=True,
    )
    for target, text in (
        ("/etc/hostname", "commonplace-test\n"),
        ("/etc/rc", "echo startup-kept > /root/startup-marker\n"),
        ("/root/private-file", "home-kept\n"),
        ("/usr/bin/local-tool", "local-kept\n"),
    ):
        source = directory / "input"
        source.write_text(text)
        subprocess.run([hfs, str(system), "add", str(source), target], check=True)
    reject_symlink(directory, system)
    before = digest(system)
    with system.open("r+b") as stream:
        fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run_update(system, success=False)
        if "disk is in use" not in result.stderr:
            raise ValueError("update did not reject a locked disk")
    if digest(system) != before:
        raise ValueError("lock rejection changed the installed disk")
    run_update(system)
    backups = list(directory.glob("system.hfs.previous-*"))
    if len(backups) != 1 or digest(backups[0]) != before:
        raise ValueError("rollback image does not preserve the original bytes")
    boot(
        directory / "updated",
        system,
        [
            case("updated program", "/bin/echo updated-ok", r"\nupdated-ok\n"),
            case("new recovery utility", "test -x /sbin/fsck_hfs; echo $?", r"\n0\n"),
            case("preserved hostname", "hostname", r"\ncommonplace-test\n"),
            case(
                "preserved files and startup",
                "cat /root/private-file /usr/bin/local-tool /root/startup-marker",
                r"\nhome-kept\nlocal-kept\nstartup-kept\n",
            ),
        ],
    )
    run_update(system, "--restore", str(backups[0]))
    if digest(system) != before:
        raise ValueError("rollback did not restore the exact original disk")
    boot(
        directory / "restored",
        system,
        [
            case(
                "original program",
                "/bin/echo hidden; echo original-status:$?",
                r"\noriginal-status:1\n",
            ),
            case(
                "original installation", "test ! -e /sbin/fsck_hfs; echo $?", r"\n0\n"
            ),
            case(
                "preserved files",
                "cat /root/private-file /usr/bin/local-tool",
                r"\nhome-kept\nlocal-kept\n",
            ),
        ],
    )
    (directory / "summary.json").write_text(
        json.dumps({"passed": True, "boots": 2, "backup_sha256": before}, indent=2)
        + "\n"
    )
    print(
        "offline update, preservation, rollback and lock rejection passed: "
        + str(directory)
    )


if __name__ == "__main__":
    main()
