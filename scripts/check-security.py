#!/usr/bin/env python3
"""Verify Apple's task identity client against live XNU audit tokens."""

from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
from darwin_build import ROOT, OUT, compile_source, link_program
from guest_console import Console, PROMPT
from qemu_machine import KERNEL, ROOT_IMAGE, command_for


def main():
    directory = ROOT / "build/security-checks" / datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S.%fZ")
    directory.mkdir(parents=True)
    recovery = directory / "recovery.hfs"
    shutil.copyfile(ROOT_IMAGE, recovery)
    obj = compile_source(ROOT / "tests/guest/security_task.c",
        OUT / "obj/tests/security-task.o", ["-I" + str(OUT / "include/security"),
            "-fblocks", "-Wall", "-Wextra", "-Werror"])
    probe = directory / "security-check"
    link_program(probe, [obj], [OUT / "lib/libsectask.a", OUT / "lib/libbsm.a",
        OUT / "system/CoreFoundation"])
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run([hfs, str(recovery), "add", str(probe), "/bin/security-check"], check=True)
    subprocess.run([hfs, str(recovery), "chmod", "755", "/bin/security-check"], check=True)
    command = command_for([KERNEL.relative_to(ROOT), recovery.relative_to(ROOT)],
        1024, bounded=False) + ["-serial", "mon:stdio"]
    console = Console(command, directory / "serial.log", cwd=ROOT)
    try:
        console.expect(PROMPT, seconds=180)
        console.command("security-check; echo security-status:$?",
            rb"native security task identity and entitlement checks passed[\s\S]*security-status:0")
        console.poweroff()
    finally:
        console.close()
    (directory / "summary.json").write_text(json.dumps({
        "passed": True,
        "kernel_sha256": hashlib.sha256(KERNEL.read_bytes()).hexdigest(),
        "probe_sha256": hashlib.sha256(probe.read_bytes()).hexdigest(),
    }, indent=2) + "\n")
    print("native security task checks passed; evidence: " + str(directory), flush=True)


if __name__ == "__main__":
    main()
