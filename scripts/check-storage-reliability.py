#!/usr/bin/env python3
"""Verify durable writes across abrupt VM loss and recovery from ENOSPC."""

import argparse
from datetime import datetime, timezone
import json
import os
import subprocess
from darwin_build import ROOT, OUT, LD, compile_source
from guest_console import Console, PROMPT
from qemu_machine import KERNEL, ROOT_IMAGE, command_for
from rootfs_image import build_image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=6)
    options = parser.parse_args()
    if not 1 <= options.cycles <= 100:
        parser.error("cycles must be 1..100")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = ROOT / "build/storage-reliability" / stamp
    directory.mkdir(parents=True)
    system, data = directory / "system.hfs", directory / "data.hfs"
    build_image(system, 64, persistent=True)
    subprocess.run(
        [
            "python3",
            str(ROOT / "scripts/create-disk.py"),
            "--path",
            str(data),
            "--size",
            "16",
        ],
        check=True,
    )
    obj = compile_source(
        ROOT / "tests/guest/storage_reliability.c",
        OUT / "obj/tests/storage-reliability.o",
    )
    probe = directory / "storage-check"
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
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run(
        [hfs, str(system), "add", str(probe), "/bin/storage-check"], check=True
    )
    subprocess.run([hfs, str(system), "chmod", "755", "/bin/storage-check"], check=True)

    def start(name, recovery=False):
        command = command_for(
            [KERNEL, ROOT_IMAGE] if recovery else [KERNEL],
            1024,
            data,
            bounded=False,
            system_disk=system,
            disk_root=not recovery,
        ) + ["-serial", "mon:stdio"]
        console = Console(command, directory / (name + ".log"))
        try:
            console.expect(PROMPT, seconds=90)
        except BaseException:
            console.close()
            raise
        return console

    for cycle in range(options.cycles):
        console = start("crash-%02d" % cycle)
        try:
            if cycle:
                console.command("storage-check verify", rb"\ndurable files verified\n")
            os.write(console.master, b"storage-check crash\n")
            console.expect(rb"\ndurable checkpoint\n", seconds=90)
            console.expect(
                ("(?:^|\n)transaction %d\n" % (cycle * 7)).encode(), seconds=90
            )
            console.process.kill()
            console.process.wait(timeout=10)
        finally:
            console.close()
        print("abrupt shutdown %d/%d" % (cycle + 1, options.cycles), flush=True)
    console = start("recovered")
    try:
        console.command("storage-check verify", rb"\ndurable files verified\n")
        os.write(console.master, b"storage-check fill\n")
        console.expect(rb"\nfull volume recovery verified\n", seconds=180)
        console.expect(PROMPT)
        console.poweroff()
    finally:
        console.close()
    console = start("fsck", recovery=True)
    try:
        os.write(
            console.master,
            b"umount /data; fsck_hfs -fn -c 16m /dev/rcp0; echo data-check:$?; fsck_hfs -fn -c 16m /dev/rcp1; echo root-check:$?\n",
        )
        console.expect(rb"\ndata-check:0\n", seconds=120)
        console.expect(rb"\nroot-check:0\n", seconds=120)
        console.expect(PROMPT)
        console.poweroff()
    finally:
        console.close()
    for log in directory.glob("*.log"):
        text = log.read_text(errors="replace")
        if "ATA timeout" in text or "panic trap" in text:
            raise ValueError("storage fault found: " + str(log))
    (directory / "summary.json").write_text(
        json.dumps(
            {
                "passed": True,
                "crash_cycles": options.cycles,
                "enospc_recovered": True,
                "both_filesystems_verified": True,
            },
            indent=2,
        )
        + "\n"
    )
    print("storage reliability checks passed: " + str(directory))


if __name__ == "__main__":
    main()
