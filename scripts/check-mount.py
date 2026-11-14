#!/usr/bin/env python3
"""Verify Apple's mount dispatcher, HFS helper and Libinfo fstab backend."""

from datetime import datetime, timezone
import json
import subprocess
import sys
from rootfs_image import ROOT, build_image


def main():
    directory = (
        ROOT
        / "build/mount-checks"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    directory.mkdir(parents=True)
    image = directory / "system.hfs"
    build_image(image, 64, persistent=True)
    cases = [
        (
            "fstab entry",
            "mkdir /tmp/system; echo '/dev/cp1 /tmp/system hfs rw 0 2' > /etc/fstab; echo configured",
            r"\nconfigured\n",
        ),
        ("mount from fstab", "mount /tmp/system; echo mount:$?", r"\nmount:0\n"),
        ("list mounted filesystems", "mount", r"/dev/cp1 on /tmp/system \(hfs"),
        (
            "read only remount",
            "mount -u -o ro /tmp/system; echo remount:$?",
            r"\nremount:0\n",
        ),
        (
            "read only enforcement",
            "sh -c 'echo denied > /tmp/system/root/denied'; echo write:$?",
            r"[Rr]ead-only file system[\s\S]*\nwrite:1\n",
        ),
        (
            "read write remount",
            "mount -u -o rw /tmp/system; echo remount:$?",
            r"\nremount:0\n",
        ),
        (
            "write file",
            "echo native-mount > /tmp/system/root/probe; cat /tmp/system/root/probe",
            r"\nnative-mount\n",
        ),
        ("unmount", "umount /tmp/system; echo unmount:$?", r"\nunmount:0\n"),
        (
            "explicit mount dispatch",
            "mount -t hfs /dev/cp1 /tmp/system; cat /tmp/system/root/probe",
            r"\nnative-mount\n",
        ),
        (
            "clean unmount",
            "umount /tmp/system; fsck_hfs -fn -c 16m /dev/rcp1; echo check:$?",
            r"appears to be OK[\s\S]*\ncheck:0\n",
        ),
    ]
    scenario = directory / "cases.json"
    scenario.write_text(
        json.dumps(
            [{"name": n, "send": c + "\n", "expect": e} for n, c, e in cases], indent=2
        )
        + "\n"
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/boot-qemu.py"),
            "--root-image",
            str(ROOT / "build/rootfs/root.hfs"),
            "--system-disk",
            str(image),
            "--seconds",
            "240",
            "--check-console",
            "--console-case-file",
            str(scenario),
            "--expect-shutdown",
            "poweroff",
            "--output",
            str(directory / "boot"),
        ],
        check=True,
    )
    print("native mount and fstab checks passed: " + str(directory))


if __name__ == "__main__":
    main()
