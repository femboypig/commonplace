#!/usr/bin/env python3
"""Verify raw sector transfers, adjacent sectors and timings on a disposable disk."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from darwin_build import ROOT, OUT, compile_source, link_program
from guest_console import Console, PROMPT
from qemu_machine import KERNEL, ROOT_IMAGE, command_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=Path, default=KERNEL)
    options = parser.parse_args()
    directory = (
        ROOT
        / "build/ata-checks"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    directory.mkdir(parents=True)
    recovery = directory / "recovery.hfs"
    shutil.copyfile(ROOT_IMAGE, recovery)
    raw = directory / "raw.img"
    with raw.open("wb") as file:
        file.truncate(16 * 1024 * 1024)
    obj = compile_source(
        ROOT / "tests/guest/ata_transfer.c", OUT / "obj/tests/ata-transfer.o"
    )
    program = directory / "ata-check"
    link_program(program, [obj])
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run(
        [hfs, str(recovery), "add", str(program), "/bin/ata-check"], check=True
    )
    subprocess.run([hfs, str(recovery), "chmod", "755", "/bin/ata-check"], check=True)
    console = Console(
        command_for([options.kernel.resolve(), recovery], 1024, raw, bounded=False)
        + ["-serial", "mon:stdio"],
        directory / "serial.log",
    )
    try:
        console.expect(PROMPT, seconds=180)
        console.sendline("ata-check; echo transfer-status:$?")
        response = console.expect(PROMPT, seconds=300)
        timings = re.search(
            rb"ata transfer passed: bytes=([0-9]+) write_us=([0-9]+) read_us=([0-9]+)",
            response,
        )
        if not timings or b"transfer-status:0" not in response:
            raise ValueError("raw ATA transfer failed: " + repr(response[-512:]))
        console.poweroff()
    finally:
        console.close()
    with raw.open("rb") as file:
        file.seek(65536 - 512)
        if file.read(512) != bytes(512):
            raise ValueError("transfer modified the preceding sector")
        expected = bytes(
            ((offset * 37) ^ (offset >> 9) ^ 0xA5) & 255
            for offset in range(4 * 1024 * 1024)
        )
        if file.read(len(expected)) != expected or file.read(512) != bytes(512):
            raise ValueError("disk contents differ from the guest's verified transfer")
    result = dict(
        passed=True,
        kernel_sha256=hashlib.sha256(options.kernel.read_bytes()).hexdigest(),
        bytes=int(timings[1]),
        write_us=int(timings[2]),
        read_us=int(timings[3]),
    )
    (directory / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "raw ATA transfers and neighboring sectors passed: " + str(directory),
        flush=True,
    )
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
