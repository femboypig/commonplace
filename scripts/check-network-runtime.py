#!/usr/bin/env python3
"""Verify native network lookups and loopback sockets on disposable RAM media."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
from darwin_build import ROOT, OUT, compile_source, link_program
from guest_console import Console, PROMPT
from qemu_machine import KERNEL, ROOT_IMAGE, command_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=Path, default=KERNEL)
    options = parser.parse_args()
    directory = ROOT / "build/network-runtime-checks" / datetime.now(
        timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory.mkdir(parents=True)
    kernel = directory / "kernel"
    shutil.copyfile(options.kernel.resolve(), kernel)
    recovery = directory / "recovery.hfs"
    shutil.copyfile(ROOT_IMAGE, recovery)
    obj = compile_source(ROOT / "tests/guest/network_libinfo.c",
        OUT / "obj/tests/network-libinfo.o")
    probe = directory / "network-libinfo-check"
    link_program(probe, [obj])
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    resources = {"/bin/network-libinfo-check": probe}
    for name, contents in {
        "networks": "loopback 127\ninvalid bogus\ntestnet 192.0.2\n",
        "services": "http 80/tcp www\ndomain 53/udp\n",
        "protocols": "ip 0 IP\nicmp 1 ICMP\ntcp 6 TCP\nudp 17 UDP\n",
    }.items():
        file = directory / name
        file.write_text(contents)
        resources["/etc/" + name] = file
    for target, source in resources.items():
        subprocess.run([hfs, str(recovery), "add", str(source), target], check=True)
    subprocess.run([hfs, str(recovery), "chmod", "755", "/bin/network-libinfo-check"], check=True)
    command = command_for([kernel.relative_to(ROOT), recovery.relative_to(ROOT)], 1024,
        bounded=False) + ["-serial", "mon:stdio"]
    console = Console(command, directory / "serial.log", cwd=ROOT)
    try:
        console.expect(PROMPT, seconds=180)
        for request, expected in (
            ("network-libinfo-check", rb"native network address and database lookups passed"),
            ("ifconfig lo0 inet 127.0.0.1 netmask 255.0.0.0 up", rb"status:0"),
            ("ifconfig lo0", rb"inet 127\.0\.0\.1"),
            ("ping -n -c 2 127.0.0.1", rb"2 packets transmitted, 2 packets received"),
            ("route -n get 127.0.0.1", rb"interface: lo0"),
            ("arp -an", rb"status:0"),
        ):
            console.sendline(request + "; echo network-runtime-status:$?")
            response = console.expect(PROMPT)
            if b"network-runtime-status:0" not in response or not re.search(expected, response):
                raise ValueError("native network check failed: " + repr(response[-1500:]))
        console.poweroff()
    finally:
        console.close()
    (directory / "summary.json").write_text(json.dumps({
        "passed": True,
        "kernel_sha256": hashlib.sha256(kernel.read_bytes()).hexdigest(),
        "libsystem_sha256": hashlib.sha256((OUT / "system/libSystem.B.dylib").read_bytes()).hexdigest(),
    }, indent=2) + "\n")
    print("native network lookups and loopback passed; evidence: " + str(directory), flush=True)


if __name__ == "__main__":
    main()
