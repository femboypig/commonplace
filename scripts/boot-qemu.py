#!/usr/bin/env python3
"""Run a bounded KVM boot and preserve serial output and CPU state."""

import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import tempfile
import time

from qemu_monitor import Monitor
from qemu_machine import KERNEL, LOADER, command_for
from serial_probe import SerialProbe

ROOT = Path(__file__).resolve().parent.parent


def boot_state(log):
    return {
        "kernel_entered": "Darwin Kernel Version 15.6.0:" in log,
        "platform_started": "commonplace: q35 bootstrap platform started" in log,
        "root_mounted": any("BSD root: " + name + "," in log for name in ("md0", "cp1"))
        and "hfs: mounted " in log,
        "init_started": "commonplace init: pid 1\n" in log.replace("\r", "")
        and re.search(rb"[A-Za-z0-9][A-Za-z0-9.-]{0,254}:/ root# ", log.encode())
        is not None,
        "crypto_started": "commonplace: crypto provider started" in log,
        "waiting_for_root": "Still waiting for root device" in log,
        "fatal": any(
            marker in log
            for marker in ("panic(cpu ", "Panic initiated,", "boot stopped:")
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--memory", type=int, default=1024, help="guest memory in MiB")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "build/boot",
        help="directory for this run's logs and diagnostics",
    )
    parser.add_argument(
        "--require-root-wait",
        action="store_true",
        help="require BSD to reach the missing root device loop",
    )
    parser.add_argument(
        "--root-image", type=Path, help="HFS+ root image passed as a second module"
    )
    parser.add_argument(
        "--require-init",
        action="store_true",
        help="require bootstrap PID 1 and console prompt",
    )
    parser.add_argument(
        "--check-console", action="store_true", help="exercise TTY input and commands"
    )
    parser.add_argument("--disk-image", type=Path, help="persistent raw HFS+ data disk")
    parser.add_argument("--system-disk", type=Path, help="persistent HFS+ system disk")
    parser.add_argument(
        "--disk-root", action="store_true", help="boot directly from the system disk"
    )
    parser.add_argument(
        "--console-case-file",
        type=Path,
        help="JSON console scenario for integration checks",
    )
    parser.add_argument(
        "--expect-shutdown",
        choices=("poweroff", "reboot"),
        help="require guest shutdown after console checks",
    )
    options = parser.parse_args()
    if options.expect_shutdown and not options.check_console:
        parser.error("--expect-shutdown needs --check-console")
    probe_cases = None
    if options.console_case_file:
        if not options.check_console:
            parser.error("--console-case-file needs --check-console")
        entries = json.loads(options.console_case_file.read_text())
        if not isinstance(entries, list) or not entries or len(entries) > 1000:
            parser.error("console scenario must contain 1..1000 cases")
        probe_cases = []
        for case in entries:
            if set(case) != {"name", "send", "expect"} or not all(
                isinstance(v, str) for v in case.values()
            ):
                parser.error("invalid console case")
            probe_cases.append(
                (case["name"], case["send"].encode(), case["expect"].encode())
            )
    if options.disk_image:
        options.disk_image = options.disk_image.resolve()
        if not options.disk_image.is_file() or "," in str(options.disk_image):
            parser.error("invalid persistent disk path")
    if options.system_disk:
        options.system_disk = options.system_disk.resolve()
        if not options.system_disk.is_file() or "," in str(options.system_disk):
            parser.error("invalid system disk path")
    if options.disk_root and (not options.system_disk or options.root_image):
        parser.error("--disk-root requires --system-disk and cannot use --root-image")
    options.require_init |= options.check_console
    if options.require_root_wait and options.root_image:
        parser.error("--require-root-wait cannot be used with --root-image")
    if options.require_init and not (options.root_image or options.disk_root):
        parser.error("--require-init needs --root-image or --disk-root")
    if not 1 <= options.seconds <= 3600 or not 512 <= options.memory <= 8192:
        parser.error("seconds must be 1..3600 and memory must be 512..8192 MiB")
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    kernel, loader = KERNEL, LOADER
    serial = output / "serial.log"
    for artifact in (kernel, loader):
        if not artifact.is_file():
            parser.error(f"missing artifact: {artifact}")
    modules = [kernel]
    if options.root_image:
        root_image = options.root_image.resolve()
        if (
            not root_image.is_file()
            or "," in str(root_image)
            or any(c.isspace() for c in str(root_image))
        ):
            parser.error("invalid root image path")
        modules.append(root_image)
    with tempfile.TemporaryDirectory(prefix="commonplace-qmp-") as directory:
        path = Path(directory) / "monitor"
        serial_path = Path(directory) / "serial"
        command = command_for(
            modules,
            options.memory,
            options.disk_image,
            system_disk=options.system_disk,
            disk_root=options.disk_root,
        )
        if options.check_console:
            command += [
                "-S",
                "-chardev",
                f"socket,id=tty,path={serial_path},server=on,wait=off",
                "-serial",
                "chardev:tty",
            ]
        else:
            command += ["-serial", f"file:{serial}"]
        command += ["-qmp", f"unix:{path},server=on,wait=off"]
        with (output / "qemu.stderr.log").open("w") as errors:
            process = subprocess.Popen(command, cwd=ROOT, stderr=errors)
            monitor = None
            console = None
            shutdown_sent = False
            try:
                monitor = Monitor(path, process)
                if options.check_console:
                    console = SerialProbe(serial_path, serial, probe_cases)
                    monitor.command("cont")
                started = time.monotonic()
                deadline = started + options.seconds
                while time.monotonic() < deadline and process.poll() is None:
                    if console:
                        console.poll()
                        if console.done:
                            if console.error or not options.expect_shutdown:
                                break
                            if not shutdown_sent:
                                console.socket.sendall(
                                    (options.expect_shutdown + "\n").encode()
                                )
                                shutdown_sent = True
                            elif not monitor.command("query-status")["running"]:
                                console.poll()
                                break
                    if serial.exists():
                        state = boot_state(serial.read_text(errors="replace"))
                        if (
                            state["fatal"]
                            or (options.require_root_wait and state["waiting_for_root"])
                            or (
                                options.require_init
                                and not console
                                and state["init_started"]
                            )
                        ):
                            break
                    time.sleep(min(0.25, max(0, deadline - time.monotonic())))
                diagnostics = {
                    "command": command,
                    "timeout_seconds": options.seconds,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "status": monitor.command("query-status"),
                    "sha256": {
                        str(p.relative_to(ROOT))
                        if p.is_relative_to(ROOT)
                        else str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [loader, *modules]
                    },
                }
                if console:
                    diagnostics["console"] = {
                        "passed": console.passed,
                        "total": len(console.cases),
                        "error": console.error,
                    }
                diagnostics["events"] = monitor.events.copy()
                if options.expect_shutdown:
                    diagnostics["shutdown"] = {
                        "requested": options.expect_shutdown,
                        "sent": shutdown_sent,
                        "stopped": not diagnostics["status"]["running"],
                    }
                monitor.command("stop")
                diagnostics["boot"] = boot_state(serial.read_text(errors="replace"))
                for name, request in {
                    "registers": "info registers",
                    "instructions": "x/12i $rip",
                    "stack": "x/48gx $rsp",
                    "frames": "x/32gx $rbp",
                }.items():
                    diagnostics[name] = monitor.inspect(request)
                (output / "diagnostics.json").write_text(
                    json.dumps(diagnostics, indent=2) + "\n"
                )
            finally:
                if console:
                    console.close()
                if monitor:
                    monitor.close()
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    log = serial.read_text(errors="replace").splitlines()
    if len(log) > 100:
        log = log[:80] + [f"... full output: {serial} ..."] + log[-20:]
    print("\n".join(log))
    print(f"boot observation finished; diagnostics: {output / 'diagnostics.json'}")
    if diagnostics["boot"]["fatal"]:
        raise SystemExit("boot failed: kernel panic or loader failure")
    if not diagnostics["boot"]["kernel_entered"]:
        raise SystemExit("boot failed: kernel version banner not reached")
    if not diagnostics["boot"]["platform_started"]:
        raise SystemExit("boot failed: q35 platform did not start")
    if options.require_root_wait and not (
        diagnostics["boot"]["waiting_for_root"]
        and diagnostics["boot"]["crypto_started"]
    ):
        raise SystemExit("boot failed: BSD did not reach root device discovery")
    if options.require_init and not (
        diagnostics["boot"]["init_started"] and diagnostics["boot"]["root_mounted"]
    ):
        raise SystemExit("boot failed: bootstrap PID 1 or console prompt not reached")
    if options.check_console:
        result = diagnostics["console"]
        if result["error"] or result["passed"] != result["total"]:
            raise SystemExit("boot failed: console checks incomplete: " + str(result))
    if options.expect_shutdown:
        marker = (
            "commonplace: powering off q35"
            if options.expect_shutdown == "poweroff"
            else "commonplace: restarting q35"
        )
        if not diagnostics["shutdown"]["stopped"] or marker not in serial.read_text(
            errors="replace"
        ):
            raise SystemExit("boot failed: guest shutdown was not acknowledged")
    milestone = (
        "PID 1 and console"
        if options.require_init
        else "BSD root device discovery"
        if options.require_root_wait
        else "q35 platform"
    )
    print("bootstrap milestones reached: darwin kernel and " + milestone)


if __name__ == "__main__":
    main()
