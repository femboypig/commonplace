#!/usr/bin/env python3
"""Boot the packaged system, then verify a warm reboot and cold persistence."""

import argparse
import hashlib
import sys
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time
from guest_console import Console, PROMPT

ROOT = Path(__file__).resolve().parent.parent
PASSWORD = "Release-check-passphrase-2026!"
RESET_PASSWORD = "Release-recovered-passphrase-2026!"


def check_network(console, manifest):
    if manifest.get("profile") != "apple-services":
        return
    console.command("ifconfig en0", rb"ether 52:54:00:12:34:56")
    console.command("ifconfig lo0", rb"inet 127\.0\.0\.1")
    if manifest.get("address_configuration") == "dhcp":
        console.command("ipconfig getifaddr en0; echo dhcp-status:$?",
            rb"10\.0\.2\.15[\s\S]*dhcp-status:0")
        console.command("ipconfig getoption en0 server_identifier; echo server-status:$?",
            rb"10\.0\.2\.2[\s\S]*server-status:0")


def boot(directory, memory, output, prepare=False, *, password=PASSWORD):
    manifest = json.loads((directory / "manifest.json").read_text())
    timeout = 180 if manifest.get("profile") == "apple-services" else 60
    authenticated = manifest.get("authentication") == "local-pam"
    # Test-only secret is provisioned into the extracted writable disk.
    console = Console([str(directory / "run.sh"), "--memory", str(memory)], output)
    try:
        started = time.monotonic()
        if authenticated:
            if prepare:
                console.expect(
                    rb"commonplace first boot: set the root password", seconds=timeout
                )
                console.change_password(password)
            first = console.login("root", password, seconds=timeout)
            boot_log = output.read_bytes()
        else:
            first = console.expect(PROMPT, seconds=timeout)
            boot_log = first
        if b"BSD root: cp1," not in boot_log or b"Added memory device md0" in boot_log:
            raise ValueError("release did not boot directly from its persistent root")
        duration = round(time.monotonic() - started, 3)
        check_network(console, manifest)
        if prepare:
            console.command("ls /data", rb"\Als /data\n" + PROMPT)
            console.command(
                "echo release-ok > /data/probe", rb"\Aecho release-ok > /data/probe\n"
            )
            console.command(
                "cp /bin/echo /usr/bin/persisted",
                rb"\Acp /bin/echo /usr/bin/persisted\n",
            )
            console.command(
                "echo root-ok > /etc/probe; echo commonplace-test > /etc/hostname",
                rb"\Aecho root-ok",
            )
            console.command(
                "echo 'echo startup-ok > /root/startup-marker' > /etc/rc", rb"\Aecho"
            )
            os.write(console.master, b"reboot\n")
            console.expect(rb"commonplace: restarting q35")
            if authenticated:
                console.login("root", password, seconds=timeout)
            else:
                console.expect(PROMPT, seconds=timeout)
        if prepare:
            check_network(console, manifest)
        console.command("cat /data/probe", rb"\nrelease-ok\n")
        console.command("/usr/bin/persisted executable-ok", rb"\nexecutable-ok\n")
        console.command(
            "cat /etc/probe /root/startup-marker; hostname",
            rb"\nroot-ok\nstartup-ok\ncommonplace-test\n",
        )
        console.poweroff()
        return {
            "memory_mib": memory,
            "prompt_seconds": duration,
            "exit": console.process.returncode,
        }
    finally:
        console.close()


def check_factory(directory, output):
    system = directory / "build/disks/system.hfs"
    before = hashlib.sha256(system.read_bytes()).hexdigest()
    console = Console(
        [str(directory / "run.sh"), "--recovery", "--no-network"], output
    )
    try:
        console.expect(PROMPT, seconds=180)
        console.sendline("fsck_hfs -fn -c 16m /dev/rcp1; echo factory-status:$?")
        response = console.expect(PROMPT, seconds=180)
        if b"\nfactory-status:0\n" not in response:
            raise ValueError("packaged factory filesystem failed native verification")
        console.poweroff()
    finally:
        console.close()
    if hashlib.sha256(system.read_bytes()).hexdigest() != before:
        raise ValueError("factory verification changed the installed system")
    return {"passed": True, "system_sha256": before}


def packaged_recovery(directory, output):
    system = directory / "build/disks/system.hfs"
    before = hashlib.sha256(system.read_bytes()).hexdigest()
    snapshots = set(system.parent.glob("system.hfs.previous-*"))
    console = Console(
        [
            sys.executable,
            str(directory / "scripts/recover-system.py"),
            "--path",
            str(system),
            "--reset-password",
            "root",
        ],
        output / "password-reset.log",
    )
    try:
        console.change_password(RESET_PASSWORD, seconds=180)
        console.expect(rb"system ready: ", seconds=180)
        if console.process.wait(timeout=10) != 0:
            raise ValueError("packaged password recovery failed")
    finally:
        console.close()
    if RESET_PASSWORD.encode() in (output / "password-reset.log").read_bytes():
        raise ValueError("packaged recovery echoed its password")
    added = set(system.parent.glob("system.hfs.previous-*")) - snapshots
    if len(added) != 1:
        raise ValueError("packaged recovery did not retain one snapshot")
    snapshot = added.pop()
    if hashlib.sha256(snapshot.read_bytes()).hexdigest() != before:
        raise ValueError("packaged recovery snapshot differs from the original")
    recovered = boot(directory, 1024, output / "recovered.log", password=RESET_PASSWORD)
    subprocess.run(
        [
            sys.executable,
            str(directory / "scripts/recover-system.py"),
            "--path",
            str(system),
            "--repair",
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(directory / "scripts/update-system.py"),
            "--path",
            str(system),
            "--restore",
            str(snapshot),
        ],
        check=True,
    )
    if hashlib.sha256(system.read_bytes()).hexdigest() != before:
        raise ValueError("packaged rollback did not restore the original bytes")
    restored = boot(directory, 1024, output / "restored.log")
    current = hashlib.sha256(system.read_bytes()).hexdigest()
    rejected = subprocess.run(
        [
            sys.executable,
            str(directory / "scripts/update-system.py"),
            "--path",
            str(system),
        ],
        capture_output=True,
        text=True,
    )
    if (
        rejected.returncode == 0
        or "source updates require a build tree" not in rejected.stderr
    ):
        raise ValueError("standalone update did not explain its build requirement")
    if hashlib.sha256(system.read_bytes()).hexdigest() != current:
        raise ValueError("rejected standalone update changed the installed system")
    return [recovered, restored]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    options = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = ROOT / "build/release-checks" / stamp
    extracted = output / "path with spaces"
    extracted.mkdir(parents=True)
    with tarfile.open(options.archive) as archive:
        archive.extractall(extracted, filter="data")
    directories = list(extracted.iterdir())
    if len(directories) != 1 or not directories[0].is_dir():
        raise ValueError("unexpected release layout")
    directory = directories[0]
    subprocess.run(
        ["python3", str(directory / "scripts/verify-release.py"), str(directory)],
        check=True,
    )
    factory = check_factory(directory, output / "factory.log")
    results = [
        boot(directory, 512, output / "warm.log", prepare=True),
        boot(directory, 2048, output / "cold.log"),
    ]
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("authentication") == "local-pam":
        results.extend(packaged_recovery(directory, output))
    subprocess.run(
        ["python3", str(directory / "scripts/verify-release.py"), str(directory)],
        check=True,
    )
    manifest = json.loads((directory / "manifest.json").read_text())
    summary = {"passed": True, "revision": manifest["revision"],
        "factory": factory, "boots": results}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        "packaged boot, persistence and standalone recovery passed; evidence: "
        + str(output)
    )


if __name__ == "__main__":
    main()
