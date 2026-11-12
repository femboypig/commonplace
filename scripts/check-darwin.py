#!/usr/bin/env python3
"""Exercise Apple's native userspace in a disposable QEMU root image."""

from datetime import datetime, timezone
import argparse
import json
import re
import struct
import shutil
import subprocess
import sys
from darwin_build import ROOT, OUT, LD, compile_source


def audit_libraries():
    nm = ROOT / "toolchain/bin/x86_64-apple-darwin15-nm"
    for name in ("libSystem.B.dylib", "libsystem_kernel.dylib"):
        symbols = subprocess.check_output(
            [str(nm), "-g", str(OUT / "system" / name)], text=True
        )
        if re.search(r"^[0-9a-f]+ [TDBSC] _main$", symbols, re.M):
            raise ValueError("a system library contains a program entry point")


def audit_programs():
    directory = ROOT / "build/userland"
    manifest = json.loads((directory / "build.json").read_text())
    platform = set(manifest["platform_commands"])
    for name in json.loads((directory / "programs.json").read_text()):
        data = (directory / name).read_bytes()
        magic, cpu, _, kind, count, size, flags, _ = struct.unpack_from("<8I", data)
        if (magic, cpu, kind) != (0xFEEDFACF, 0x01000007, 2):
            raise ValueError("expected an x86_64 Mach-O program: " + name)
        dynamic = name not in platform
        if bool(flags & 4) != dynamic:
            raise ValueError("unexpected Mach-O linkage: " + name)
        position = 32
        dependencies = []
        loader = None
        for _ in range(count):
            command, length = struct.unpack_from("<2I", data, position)
            if length < 8 or position + length > 32 + size:
                raise ValueError("invalid Mach-O load command: " + name)
            if command in (0xE, 0xC):
                offset = struct.unpack_from("<I", data, position + 8)[0]
                path = (
                    data[position + offset : position + length]
                    .split(b"\0", 1)[0]
                    .decode()
                )
                if command == 0xE:
                    loader = path
                else:
                    dependencies.append(path)
            position += length
        if dynamic and (
            loader != "/usr/lib/dyld" or dependencies != ["/usr/lib/libSystem.B.dylib"]
        ):
            raise ValueError("unexpected dynamic loader dependency: " + name)
        if not dynamic and (loader or dependencies):
            raise ValueError("unexpected platform program dependency: " + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disk-root", action="store_true")
    options = parser.parse_args()
    audit_libraries()
    audit_programs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = ROOT / "build/darwin-checks" / stamp
    directory.mkdir(parents=True)
    probe = directory / "libc-check"
    obj = compile_source(ROOT / "tests/guest/darwin_libc.c", OUT / "obj/tests/libc.o")
    libraries = [OUT / "system/libSystem.B.dylib"]
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
            "-dead_strip",
            "-no_uuid",
            "-o",
            str(probe),
            str(obj),
            *map(str, libraries),
        ],
        check=True,
    )
    image = directory / "root.hfs"
    if options.disk_root:
        from rootfs_image import build_image

        build_image(image, size_mib=64, persistent=True)
    else:
        shutil.copyfile(ROOT / "build/rootfs/root.hfs", image)
    hfs = ROOT / "toolchain/bin/hfsplus"
    for operation in (
        ["add", str(probe), "/bin/libc-check"],
        ["chmod", "755", "/bin/libc-check"],
    ):
        subprocess.run([str(hfs), str(image), *operation], check=True)
    cases = json.loads((ROOT / "tests/guest/darwin_commands.json").read_text())
    scenario = directory / "cases.json"
    scenario.write_text(json.dumps(cases, indent=2) + "\n")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/boot-qemu.py"),
            "--seconds",
            "150",
            *(
                ["--system-disk", str(image), "--disk-root"]
                if options.disk_root
                else ["--root-image", str(image)]
            ),
            "--check-console",
            "--console-case-file",
            str(scenario),
            "--output",
            str(directory / "boot"),
        ],
        check=True,
    )
    print("native Darwin userspace checks passed; evidence: " + str(directory))


if __name__ == "__main__":
    main()
