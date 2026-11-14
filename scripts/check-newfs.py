#!/usr/bin/env python3
"""Format isolated disks with Apple's native newfs and verify Unicode and HFS+."""

from datetime import datetime, timezone
import json
import shutil
import subprocess
import sys
from darwin_build import ROOT, OUT, LD, compile_source


def main():
    directory = (
        ROOT
        / "build/newfs-checks"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    directory.mkdir(parents=True)
    image = directory / "recovery.hfs"
    shutil.copyfile(ROOT / "build/rootfs/root.hfs", image)
    disk = directory / "blank.hfs"
    with disk.open("wb") as stream:
        stream.truncate(32 * 1024 * 1024)
    obj = compile_source(
        ROOT / "tests/guest/hfs_primitives.c",
        OUT / "obj/tests/hfs-primitives.o",
        [
            "-DCOMMONPLACE_UTFCONV_USERLAND=1",
            "-include",
            "sys/param.h",
            "-I" + str(ROOT / "sources/xnu/osfmk/prng/YarrowCoreLib/src"),
        ],
    )
    probe = directory / "hfs-primitives"
    subprocess.run(
        [
            str(LD),
            "-L" + str(OUT / "system"),
            "-Z",
            "-fatal_warnings",
            "-arch",
            "x86_64",
            "-macosx_version_min",
            "10.11",
            "-e",
            "_main",
            "-no_uuid",
            "-o",
            str(probe),
            str(obj),
            str(OUT / "obj/newfs/utfconv.o"),
            str(OUT / "obj/newfs/sha1.o"),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run(
        [hfs, str(image), "add", str(probe), "/bin/hfs-primitives"], check=True
    )
    subprocess.run([hfs, str(image), "chmod", "755", "/bin/hfs-primitives"], check=True)
    cases = [
        (
            "native Unicode and digest",
            "hfs-primitives",
            r"\nnative HFS normalization and UUID digest passed\n",
        ),
        (
            "format journaled volume",
            "newfs_hfs -J -v 'café' /dev/rcp1; echo format:$?",
            r"\nformat:0\n",
        ),
        (
            "verify formatted volume",
            "fsck_hfs -fn -c 16m /dev/rcp1; echo check:$?",
            r"appears to be OK[\s\S]*\ncheck:0\n",
        ),
        (
            "mount formatted volume",
            "mkdir /tmp/volume; mount -t hfs /dev/cp1 /tmp/volume; echo mounted:$?",
            r"\nmounted:0\n",
        ),
        (
            "write formatted volume",
            "echo formatter-ok > /tmp/volume/probe; cat /tmp/volume/probe",
            r"\nformatter-ok\n",
        ),
        (
            "reject mounted volume",
            "newfs_hfs -J /dev/rcp1; echo mounted-format:$?",
            r"is mounted on /tmp/volume[\s\S]*\nmounted-format:1\n",
        ),
        (
            "preserve mounted data",
            "cat /tmp/volume/probe; umount /tmp/volume",
            r"\nformatter-ok\n",
        ),
        (
            "verify after writes",
            "fsck_hfs -fn -c 16m /dev/rcp1; echo check:$?",
            r"appears to be OK[\s\S]*\ncheck:0\n",
        ),
        (
            "format case sensitive volume",
            "newfs_hfs -s -J -v native-hfsx /dev/rcp1; echo format:$?",
            r"\nformat:0\n",
        ),
        (
            "verify case sensitive volume",
            "fsck_hfs -fn -c 16m /dev/rcp1; echo check:$?",
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
            str(image),
            "--system-disk",
            str(disk),
            "--seconds",
            "360",
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
    print("native formatting and Unicode checks passed: " + str(directory))


if __name__ == "__main__":
    main()
