#!/usr/bin/env python3
"""Exercise Apple's real configd through its native Mach clients and launchd."""

from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import subprocess
from darwin_build import ROOT, OUT, compile_source, link_program
from guest_console import Console, PROMPT
from qemu_machine import KERNEL, command_for
from service_image import build_service_image


def boot(kernel, image, output, *, initial):
    console = Console(command_for([kernel.relative_to(ROOT)], 1024, bounded=False,
        system_disk=image, disk_root=True, network=True,
        network_backend="user,id=network,restrict=on") + ["-serial", "mon:stdio"],
        output, cwd=ROOT)
    try:
        console.expect(PROMPT, seconds=180)
        if initial:
            console.command(
                "cp /etc/master.passwd /tmp/accounts && printf '%s\\n' "
                "'tester:*:501:20::0:0:configd test:/home/tester:/bin/sh' >> /tmp/accounts "
                "&& pwd_mkdb -p /tmp/accounts && mkdir -p /home/tester "
                "&& chown 501:20 /home/tester "
                "&& mkdir -p /Library/Preferences/SystemConfiguration; echo account-status:$?",
                rb"account-status:0",
            )
        console.command("configd-check; echo configd-status:$?",
            rb"native configd store, notifications, access checks and session cleanup passed[\s\S]*configd-status:0")
        if initial:
            console.command("configd-check preferences-write; echo preferences-status:$?",
                rb"native preferences locking, notifications and permissions passed[\s\S]*preferences-status:0")
        else:
            console.command("configd-check preferences-read; echo preferences-status:$?",
                rb"native preferences persisted across cold boot[\s\S]*preferences-status:0")
        console.command("configd-check network-" + ("write" if initial else "read") + "; echo network-config-status:$?",
            rb"native ethernet service and protocol configuration passed[\s\S]*network-config-status:0")
        console.poweroff()
    except Exception:
        if console.process.poll() is None:
            try:
                os.write(console.master, b"\x03")
                console.expect(PROMPT, seconds=5)
                console.command("cat /var/log/com.apple.configd.stderr; tail -n 50 /var/log/system.log; launchctl list", rb"com.apple.configd")
            except Exception:
                pass
        raise
    finally:
        console.close()


def main():
    directory = ROOT / "build/configd-checks" / datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S.%fZ")
    directory.mkdir(parents=True)
    kernel = directory / "kernel"
    shutil.copyfile(KERNEL, kernel)
    daemon = directory / "configd"
    shutil.copyfile(OUT / "bin/configd", daemon)
    probe = directory / "configd-check"
    objects = [compile_source(ROOT / "tests/guest" / (name + ".c"),
        OUT / "obj/tests" / (name + ".o"), [
            "-I" + str(OUT / "include/configd"),
            "-I" + str(OUT / "include/security"),
            "-fblocks", "-Wall", "-Wextra", "-Werror",
        ]) for name in ("configd_store", "configd_preferences", "configd_network")]
    link_program(probe, objects, [OUT / "lib/libconfigd_store.a",
        OUT / "system/IOKit", OUT / "system/CoreFoundation"])
    image = directory / "system.hfs"
    build_service_image(image, 128, console_login=False)
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run([hfs, str(image), "add", str(probe), "/bin/configd-check"], check=True)
    subprocess.run([hfs, str(image), "chmod", "755", "/bin/configd-check"], check=True)
    inputs = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in (
        ("kernel_sha256", kernel), ("daemon_sha256", daemon), ("probe_sha256", probe),
        ("factory_sha256", image),
    )}
    boot(kernel, image, directory / "serial.log", initial=True)
    boot(kernel, image, directory / "cold.log", initial=False)
    (directory / "summary.json").write_text(json.dumps({"passed": True, **inputs}, indent=2) + "\n")
    print("native configd checks passed; evidence: " + str(directory), flush=True)


if __name__ == "__main__":
    main()
