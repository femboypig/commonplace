"""Verified recovery media and bounded native maintenance sessions."""

import hashlib
import json
import re
import shutil
import subprocess
from rootfs_image import ROOT, system_files, system_symlinks
from guest_console import Console, PROMPT
from qemu_machine import command_for, KERNEL


def recovery_image(directory, *, current_build=False):
    image = directory / "recovery.hfs"
    shutil.copyfile(ROOT / "build/rootfs/root.hfs", image)
    metadata = json.loads((ROOT / "build/rootfs/image.json").read_text())
    if hashlib.sha256(image.read_bytes()).hexdigest() != metadata["sha256"]:
        raise ValueError("recovery image does not match its manifest")
    if current_build:
        for target, source in system_files().items():
            if hashlib.sha256(source.read_bytes()).hexdigest() != metadata[
                "programs"
            ].get(target):
                raise ValueError(
                    "rebuild the recovery image before updating: " + target
                )
    if metadata.get("symlinks") != system_symlinks():
        raise ValueError("rebuild recovery with the current framework layout")
    return image


def install_script(recovery, directory, name, contents):
    script = directory / name
    script.write_text(contents)
    subprocess.run(
        [
            str(ROOT / "toolchain/bin/hfsplus"),
            str(recovery),
            "add",
            str(script),
            "/tmp/" + name,
        ],
        check=True,
    )


def console_for(directory, recovery, system):
    boot = directory / "boot"
    boot.mkdir()
    command = command_for(
        [KERNEL, recovery], 1024, bounded=False, system_disk=system
    ) + ["-serial", "mon:stdio"]
    return Console(command, boot / "serial.log")


def run_script(directory, recovery, system, name, *, seconds=600):
    console = console_for(directory, recovery, system)
    try:
        console.expect(PROMPT, seconds=180)
        console.sendline("sh /tmp/" + name + "; echo recovery-status:$?")
        response = console.expect(PROMPT, seconds=seconds)
        console.poweroff()
    finally:
        console.close()
    if re.findall(rb"\nrecovery-status:([0-9]+)\n", response) != [b"0"]:
        raise ValueError(
            "native recovery transaction failed; diagnostics: " + str(directory)
        )
    return response.decode(errors="replace")
