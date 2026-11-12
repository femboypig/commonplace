#!/usr/bin/env python3
"""Verify a disk root, separate data volume and RAM recovery on isolated images."""

from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys
from rootfs_image import ROOT
from darwin_build import OUT, LD, compile_source


def case(name, send, expect):
    return {"name": name, "send": send + "\n", "expect": expect}


def boot(
    directory, system, data, cases, memory=512, recovery=False, shutdown="poweroff"
):
    directory.mkdir()
    scenario = directory / "cases.json"
    scenario.write_text(json.dumps(cases, indent=2) + "\n")
    command = [
        sys.executable,
        str(ROOT / "scripts/boot-qemu.py"),
        "--seconds",
        "150",
        "--memory",
        str(memory),
        "--system-disk",
        str(system),
        "--disk-image",
        str(data),
        "--check-console",
        "--console-case-file",
        str(scenario),
        "--expect-shutdown",
        shutdown,
        "--output",
        str(directory),
    ]
    command += (
        ["--root-image", str(ROOT / "build/rootfs/root.hfs")]
        if recovery
        else ["--disk-root"]
    )
    with (directory / "output.log").open("w") as output:
        subprocess.run(command, check=True, stdout=output, stderr=subprocess.STDOUT)
    log = (directory / "serial.log").read_text()
    expected = "BSD root: md0," if recovery else "BSD root: cp1,"
    if expected not in log or (not recovery and "Added memory device md0" in log):
        raise ValueError("unexpected root device: " + str(directory))
    if "replaying journal" in log or "Replaying journal" in log:
        raise ValueError("clean shutdown left journal replay work: " + str(directory))
    return json.loads((directory / "diagnostics.json").read_text())


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = ROOT / "build/system-disk-checks" / stamp
    directory.mkdir(parents=True)
    system, data = directory / "system.hfs", directory / "data.hfs"
    for script, path in (("create-system-disk.py", system), ("create-disk.py", data)):
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / script),
                "--path",
                str(path),
                "--size",
                "64",
            ],
            check=True,
        )
    obj = compile_source(ROOT / "tests/guest/disk_io.c", OUT / "obj/tests/disk-io.o")
    probe = directory / "disk-io-check"
    subprocess.run(
        [
            str(LD),
            "-Z",
            "-fatal_warnings",
            "-arch",
            "x86_64",
            "-macosx_version_min",
            "10.11",
            "-L" + str(OUT / "system"),
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
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run(
        [hfs, str(system), "add", str(probe), "/bin/disk-io-check"], check=True
    )
    subprocess.run([hfs, str(system), "chmod", "755", "/bin/disk-io-check"], check=True)
    token = hashlib.sha256(stamp.encode()).hexdigest()[:24]
    write = [
        case("write root settings", f"echo {token} > /etc/root-probe", r"\Aecho"),
        case("install executable", "cp /bin/echo /usr/bin/persisted", r"\Acp"),
        case("write home data", "seq 1 10000 > /root/large", r"\Aseq"),
        case("write data volume", "echo data-volume > /data/probe", r"\Aecho"),
        case("persistent hostname", "echo commonplace-test > /etc/hostname", r"\Aecho"),
        case(
            "system startup",
            "echo 'echo system-startup > /root/startup-marker' > /etc/rc",
            r"\Aecho",
        ),
        case(
            "data startup",
            "echo 'echo data-startup > /data/startup-marker' > /data/rc",
            r"\Aecho",
        ),
    ]
    read = [
        case("root settings", "cat /etc/root-probe", rf"\n{token}\n"),
        case(
            "installed executable",
            "/usr/bin/persisted native-disk-root",
            r"\nnative-disk-root\n",
        ),
        case("complete home data", "wc -l < /root/large", r"\n\s*10000\n"),
        case("independent data volume", "cat /data/probe", r"\ndata-volume\n"),
        case("configured hostname", "hostname", r"\ncommonplace-test\n"),
        case(
            "both startup scripts",
            "cat /root/startup-marker /data/startup-marker",
            r"\nsystem-startup\ndata-startup\n",
        ),
    ]
    phases = [boot(directory / "write-poweroff", system, data, write)]
    phases.append(
        boot(
            directory / "cold-read-reboot",
            system,
            data,
            read,
            memory=2048,
            shutdown="reboot",
        )
    )
    read.append(
        case(
            "uncached disk isolation",
            "/bin/disk-io-check /root /data",
            r"\nconcurrent uncached disk I/O passed\n",
        )
    )
    recovery = [
        case("separate recovery root", "test ! -e /etc/root-probe; echo $?", r"\n0\n"),
        case(
            "mount installed root",
            "mkdir /tmp/system; mount -t hfs /dev/cp1 /tmp/system",
            r"\Amkdir",
        ),
        case(
            "read installed settings", "cat /tmp/system/etc/root-probe", rf"\n{token}\n"
        ),
        case(
            "repair settings",
            f"echo {token}-recovered > /tmp/system/etc/root-probe",
            r"\Aecho",
        ),
        case("preserve data volume", "cat /data/probe", r"\ndata-volume\n"),
        case(
            "recovery disk isolation",
            "/tmp/system/bin/disk-io-check /tmp/system/root /data",
            r"\nconcurrent uncached disk I/O passed\n",
        ),
        case(
            "unmount repaired root",
            "umount /tmp/system; rmdir /tmp/system",
            r"\Aumount",
        ),
    ]
    phases.append(
        boot(
            directory / "ram-recovery",
            system,
            data,
            recovery,
            memory=1024,
            recovery=True,
        )
    )
    repaired = read.copy()
    repaired[0] = case(
        "repaired root settings", "cat /etc/root-probe", rf"\n{token}-recovered\n"
    )
    phases.append(boot(directory / "repaired-cold-boot", system, data, repaired))
    extracted = directory / "root-probe"
    subprocess.run(
        [
            str(ROOT / "toolchain/bin/hfsplus"),
            str(system),
            "extract",
            "/etc/root-probe",
            str(extracted),
        ],
        check=True,
    )
    if extracted.read_text() != token + "-recovered\n":
        raise ValueError("host verification of root settings failed")
    before = hashlib.sha256(system.read_bytes()).digest()
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/create-system-disk.py"),
            "--path",
            str(system),
        ],
        check=True,
    )
    if hashlib.sha256(system.read_bytes()).digest() != before:
        raise ValueError("installer changed an existing system")
    summary = {
        "passed": True,
        "phases": len(phases),
        "token": token,
        "console_checks": sum(phase["console"]["passed"] for phase in phases),
    }
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        "persistent root, data separation and RAM recovery passed; evidence: "
        + str(directory)
    )


if __name__ == "__main__":
    main()
