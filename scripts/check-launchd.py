#!/usr/bin/env python3
"""Verify Apple's PID 1, bootstrap namespace, notifyd and persistent ASL logging."""

from datetime import datetime, timezone
import json
import subprocess
import sys
from darwin_build import ROOT, OUT, LD, compile_source
from service_image import build_service_image


def main():
    directory = (
        ROOT
        / "build/launchd-checks"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    directory.mkdir(parents=True)
    image = directory / "system.hfs"
    obj = compile_source(
        ROOT / "tests/guest/launchd_runtime.c",
        OUT / "obj/tests/launchd_runtime.o",
        ["-fblocks", "-Wno-deprecated-declarations"],
    )
    probe = directory / "launchd-check"
    subprocess.run(
        [
            str(LD),
            "-L" + str(OUT / "system"),
            "-Z",
            "-fatal_warnings",
            "-arch",
            "x86_64",
            "-macosx_version_min",
            "10.11",
            "-e",
            "_main",
            "-no_uuid",
            "-o",
            str(probe),
            str(obj),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )
    build_service_image(image)
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run(
        [hfs, str(image), "add", str(probe), "/bin/launchd-check"], check=True
    )
    subprocess.run([hfs, str(image), "chmod", "755", "/bin/launchd-check"], check=True)
    rounds = (
        [
            (
                "native apple services",
                "launchd-check; echo native-status:$?\n",
                r"native apple service integration passed[\s\S]*native-status:0",
            ),
            (
                "bsd system logging",
                "cat /var/log/system.log; echo bsd-log-status:$?\n",
                r"commonplace bsd service integration record[\s\S]*bsd-log-status:0",
            ),
            (
                "notifyd supervision",
                "launchctl stop com.apple.notifyd; sleep 2; launchd-check notify; echo restart-status:$?\n",
                r"native notifyd: shared state, process delivery and dispatch callbacks passed[\s\S]*restart-status:0",
            ),
        ],
        [
            (
                "persistent system log",
                "launchd-check query; echo recovery-status:$?\n",
                r"native syslogd: cold-boot record recovery passed[\s\S]*recovery-status:0",
            ),
            (
                "native syslog command",
                "syslog -k Message 'commonplace native service integration record'; echo syslog-status:$?\n",
                r"\n[^\n]*commonplace native service integration record[\s\S]*syslog-status:0",
            ),
            (
                "persistent bsd system log",
                "cat /var/log/system.log; echo bsd-recovery-status:$?\n",
                r"commonplace bsd service integration record[\s\S]*bsd-recovery-status:0",
            ),
        ],
    )
    for number, cases in enumerate(rounds):
        casefile = directory / (str(number) + ".json")
        casefile.write_text(
            json.dumps([dict(name=n, send=s, expect=e) for n, s, e in cases]) + "\n"
        )
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/boot-qemu.py"),
                "--system-disk",
                str(image),
                "--disk-root",
                "--seconds",
                "600",
                "--check-console",
                "--console-case-file",
                str(casefile),
                "--expect-shutdown",
                "poweroff",
                "--output",
                str(directory / ("boot-" + str(number))),
            ],
            check=True,
        )
    print("native apple services passed: " + str(directory))


if __name__ == "__main__":
    main()
