#!/usr/bin/env python3
"""Verify Apple's DHCP client through leases from independent QEMU servers."""

from datetime import datetime, timezone
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
from darwin_build import ROOT, OUT, compile_source, link_program, prepare_source
from guest_console import Console, PROMPT
from qemu_machine import KERNEL, command_for
from service_image import build_service_image


def boot(kernel, image, log, *, subnet, memory, events=False):
    address, server, dns = (subnet + suffix for suffix in (".123", ".2", ".3"))
    backend = ("user,id=network,net=" + subnet + ".0/24,host=" + server
        + ",dns=" + dns + ",dhcpstart=" + address)
    console = Console(command_for([kernel], memory, bounded=False,
        system_disk=image, disk_root=True, network=True, network_backend=backend)
        + ["-serial", "mon:stdio"], log)
    try:
        console.expect(PROMPT, seconds=180)
        if events:
            console.command("bootp-events; echo event-status:$?",
                rb"native bootp descriptor readiness and BPF capture passed[\s\S]*event-status:0")
        console.command(
            "attempt=0; while ! ipconfig getifaddr en0; do "
            "attempt=$((attempt + 1)); [ \"$attempt\" -lt 30 ] || break; sleep 1; done; "
            "ipconfig getifaddr en0; echo dhcp-status:$?",
            address.encode().replace(b".", rb"\.") + rb"[\s\S]*dhcp-status:0")
        for option, expected in (("server_identifier", server),
                                 ("router", server), ("domain_name_server", dns),
                                 ("subnet_mask", "255.255.255.0")):
            console.command("ipconfig getoption en0 " + option + "; echo option-status:$?",
                expected.encode().replace(b".", rb"\.") + rb"[\s\S]*option-status:0")
        console.command("ipconfig getpacket en0; echo packet-status:$?", rb"packet-status:0")
        console.command("ifconfig en0", b"inet " + address.encode().replace(b".", rb"\."))
        console.poweroff()
    except Exception:
        if console.process.poll() is None:
            try:
                os.write(console.master, b"\x03")
                console.expect(PROMPT, seconds=5)
                console.command("cat /var/log/com.apple.configd.stderr; "
                    "tail -n 80 /var/log/system.log; launchctl list", rb"com.apple.configd")
            except Exception:
                pass
        raise
    finally:
        console.close()


def main():
    directory = ROOT / "build/dhcp-checks" / datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S.%fZ")
    directory.mkdir(parents=True)
    kernel = directory / "kernel"
    shutil.copyfile(KERNEL, kernel)
    source = prepare_source("bootp")
    obj = compile_source(ROOT / "tests/guest/bootp_events.c", OUT / "obj/tests/bootp_events.o",
        ["-I" + str(source / "IPConfiguration.bproj"), "-fblocks", "-Wall", "-Wextra", "-Werror"])
    probe = directory / "bootp-events"
    link_program(probe, [obj], [OUT / "lib/libbootp.a", OUT / "system/CoreFoundation"])
    image = directory / "system.hfs"
    build_service_image(image, 128, console_login=False)
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run([hfs, str(image), "add", str(probe), "/bin/bootp-events"], check=True)
    subprocess.run([hfs, str(image), "chmod", "755", "/bin/bootp-events"], check=True)
    inputs = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in (
        ("kernel_sha256", kernel), ("factory_sha256", image), ("probe_sha256", probe),
        ("bundle_sha256", OUT / "bundles/IPConfiguration.bundle/Contents/MacOS/IPConfiguration"),
        ("client_sha256", OUT / "bin/ipconfig"),
    )}
    boot(kernel, image, directory / "initial.log", subnet="10.0.2", memory=1024, events=True)
    boot(kernel, image, directory / "cold.log", subnet="10.0.2", memory=512)
    # Existing installations retain their launchd policy. The original manager
    # also supports a daemon checking in an undeclared service during upgrades.
    job_path = "/System/Library/LaunchDaemons/com.apple.configd.plist"
    legacy = directory / "legacy-configd.plist"
    subprocess.run([hfs, str(image), "extract", job_path, str(legacy)], check=True)
    job = plistlib.loads(legacy.read_bytes())
    del job["MachServices"]["com.apple.network.IPConfiguration"]
    legacy.write_bytes(plistlib.dumps(job))
    subprocess.run([hfs, str(image), "add", str(legacy), job_path], check=True)
    boot(kernel, image, directory / "changed-server.log", subnet="10.23.0", memory=6144)
    (directory / "summary.json").write_text(json.dumps({"passed": True, **inputs}, indent=2) + "\n")
    print("native DHCP leases, cold persistence and server changes passed; evidence: " + str(directory), flush=True)


if __name__ == "__main__":
    main()
