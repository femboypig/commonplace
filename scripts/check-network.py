#!/usr/bin/env python3
"""Exercise Apple's Ethernet driver with isolated host-to-guest TCP traffic."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import random
import re
import shutil
import socket
import subprocess
from darwin_build import ROOT, OUT, compile_source, link_program
from guest_console import Console, PROMPT
from qemu_machine import KERNEL, ROOT_IMAGE, command_for
from qemu_monitor import Monitor


def exchange(port, payload):
    with socket.create_connection(("127.0.0.1", port), timeout=20) as stream:
        stream.settimeout(20)

        def send():
            stream.sendall(payload)
            stream.shutdown(socket.SHUT_WR)

        with ThreadPoolExecutor(max_workers=1) as executor:
            sender = executor.submit(send)
            received = bytearray()
            while True:
                chunk = stream.recv(65536)
                if not chunk:
                    break
                received.extend(chunk)
            sender.result()
        if received != payload:
            raise ValueError("Ethernet TCP transfer differs from the sent payload")


def transfer(console, port, payloads):
    console.sendline(": > /tmp/network-transfer.log; network-transfer > /tmp/network-transfer.log 2>&1 &")
    console.expect(PROMPT)
    console.command(
        "for attempt in 1 2 3 4 5; do contents=$(cat /tmp/network-transfer.log); case \"$contents\" in *'network transfer ready'*) break;; esac; sleep 1; done; cat /tmp/network-transfer.log",
        rb"network transfer ready",
    )
    for payload in payloads:
        exchange(port, payload)
    console.command(
        "for attempt in 1 2 3 4 5; do contents=$(cat /tmp/network-transfer.log); case \"$contents\" in *'network transfer passed'*) break;; esac; sleep 1; done; cat /tmp/network-transfer.log",
        ("network transfer passed: connections=3 bytes=" + str(sum(map(len, payloads)))).encode(),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory", type=int, default=1024)
    parser.add_argument("--cycles", type=int, default=3,
        help="transfer cycles, bringing the interface down and up between cycles")
    options = parser.parse_args()
    if not 512 <= options.memory <= 8192:
        parser.error("memory must be 512..8192 MiB")
    if not 1 <= options.cycles <= 100:
        parser.error("cycles must be 1..100")
    directory = ROOT / "build/network-checks" / datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S.%fZ")
    directory.mkdir(parents=True)
    kernel = directory / "kernel"
    shutil.copyfile(KERNEL, kernel)
    recovery = directory / "recovery.hfs"
    shutil.copyfile(ROOT_IMAGE, recovery)
    obj = compile_source(ROOT / "tests/guest/network_transfer.c",
        OUT / "obj/tests/network-transfer.o")
    probe = directory / "network-transfer"
    link_program(probe, [obj])
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    for target, source in {
        "/bin/network-transfer": probe,
    }.items():
        subprocess.run([hfs, str(recovery), "add", str(source), target], check=True)
        subprocess.run([hfs, str(recovery), "chmod", "755", target], check=True)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    command = command_for([kernel.relative_to(ROOT), recovery.relative_to(ROOT)],
        options.memory, bounded=False, network=True,
        network_backend=f"user,id=network,restrict=on,hostfwd=tcp:127.0.0.1:{port}-:7777",
    ) + [
        "-object", f"filter-dump,id=packets,netdev=network,file={directory / 'packets.pcap'}",
        "-qmp", f"unix:{directory / 'qmp.sock'},server=on,wait=off",
        "-serial", "mon:stdio",
    ]
    console = Console(command, directory / "serial.log", cwd=ROOT)
    monitor = None
    try:
        monitor = Monitor(directory / "qmp.sock", console.process)
        console.expect(PROMPT, seconds=180)
        console.command("ioreg -l -w 0", rb"CommonplacePCI")
        for request, expected in (
            ("/usr/libexec/commonplace/register-network", rb"register-status:0"),
            ("/usr/libexec/commonplace/register-network", rb"register-status:0"),
            ("ifconfig en0 inet 10.0.2.15 netmask 255.255.255.0 up", rb"register-status:0"),
            ("ifconfig en0", rb"ether 52:54:"),
        ):
            console.sendline(request + "; echo register-status:$?")
            response = console.expect(PROMPT, seconds=150)
            if not re.search(expected, response):
                console.command("ioreg -l -w 0", rb"CommonplacePCI")
                raise ValueError("network configuration failed: " + repr(response[-1500:]))
        payloads = (b"", b"commonplace\x00darwin\xff",
            random.Random(0x434F4D4D).randbytes(4 * 1024 * 1024))
        for cycle in range(options.cycles):
            if cycle:
                console.command("ifconfig en0 down; echo down-status:$?", rb"down-status:0")
                console.command("ifconfig en0 up; echo up-status:$?", rb"up-status:0")
            transfer(console, port, payloads)
        expected_bytes = options.cycles * sum(map(len, payloads))
        console.command("arp -an", rb"52:55:")
        console.poweroff()
    except Exception:
        if console.process.poll() is None:
            try:
                console.command("cat /tmp/network-transfer.log; arp -an; ifconfig en0", rb"en0:")
            except Exception:
                pass
            if monitor:
                monitor.command("stop")
                diagnostics = {name: monitor.inspect(command) for name, command in (
                    ("interrupts", "info irq"), ("controllers", "info pic"),
                    ("pci", "info pci"), ("registers", "info registers"),
                )}
                adapter = re.search(
                    r"Ethernet controller: PCI device 10ec:8139.*?BAR1: 32 bit memory at (0x[0-9a-f]+)",
                    diagnostics["pci"], re.S)
                if adapter:
                    diagnostics["ethernet_registers"] = monitor.inspect(
                        "xp /32wx " + adapter.group(1))
                    diagnostics["ethernet_interrupts"] = monitor.inspect(
                        "xp /4hx " + hex(int(adapter.group(1), 16) + 0x38))
                (directory / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
        raise
    finally:
        if monitor:
            monitor.close()
        console.close()
    log = (directory / "serial.log").read_bytes()
    if b"receiverInterrupt - error detected" in log or b"Rx restart" in log:
        raise ValueError("the Ethernet driver reset or corrupted its receive ring")
    (directory / "summary.json").write_text(json.dumps({
        "passed": True, "connections": options.cycles * len(payloads),
        "cycles": options.cycles, "bytes": expected_bytes,
        "memory_mib": options.memory,
        "kernel_sha256": hashlib.sha256(kernel.read_bytes()).hexdigest(),
    }, indent=2) + "\n")
    print("Apple Ethernet TCP transfers passed; evidence: " + str(directory), flush=True)


if __name__ == "__main__":
    main()
