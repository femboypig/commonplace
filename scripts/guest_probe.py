"""Run a native test executable on private, reproducible recovery media."""

from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
from darwin_build import ROOT, OUT, compile_source, link_program
from guest_console import Console, PROMPT
from qemu_machine import KERNEL, ROOT_IMAGE, command_for


def run_probe(name, source, expected, *, flags=(), libraries=()):
    directory = ROOT / "build" / (name + "-checks") / datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S.%fZ")
    directory.mkdir(parents=True)
    kernel = directory / "kernel"
    shutil.copyfile(KERNEL, kernel)
    recovery = directory / "recovery.hfs"
    shutil.copyfile(ROOT_IMAGE, recovery)
    base_hash = hashlib.sha256(recovery.read_bytes()).hexdigest()
    obj = compile_source(source, OUT / "obj/tests" / (name + ".o"), flags)
    probe = directory / name
    link_program(probe, [obj], libraries)
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run([hfs, str(recovery), "add", str(probe), "/bin/" + name], check=True)
    subprocess.run([hfs, str(recovery), "chmod", "755", "/bin/" + name], check=True)
    command = command_for([kernel.relative_to(ROOT), recovery.relative_to(ROOT)],
        1024, bounded=False) + ["-serial", "mon:stdio"]
    console = Console(command, directory / "serial.log", cwd=ROOT)
    try:
        console.expect(PROMPT, seconds=180)
        console.command(name + "; echo native-probe-status:$?",
            expected + rb"[\s\S]*native-probe-status:0")
        console.poweroff()
    finally:
        console.close()
    (directory / "summary.json").write_text(json.dumps({
        "passed": True,
        "kernel_sha256": hashlib.sha256(kernel.read_bytes()).hexdigest(),
        "base_sha256": base_hash,
        "probe_sha256": hashlib.sha256(probe.read_bytes()).hexdigest(),
    }, indent=2) + "\n")
    return directory
