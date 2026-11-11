#!/usr/bin/env python3
"""Exercise Apple's static userspace in a disposable QEMU root image."""

from datetime import datetime, timezone
import json
import re
import struct
from collections import defaultdict
import shutil
import subprocess
import sys
from darwin_build import ROOT, OUT, LD, compile_source


def audit_libraries():
    definitions = defaultdict(list)
    nm = ROOT / "toolchain/bin/x86_64-apple-darwin15-nm"
    for library in sorted((OUT / "lib").glob("*.a")):
        symbols = subprocess.check_output([str(nm), "-g", str(library)], text=True)
        member = ""
        for line in symbols.splitlines():
            if line.endswith(":"):
                member = line
            match = re.match(r"^[0-9a-f]+ [TDBSC] (.+)$", line)
            if match:
                definitions[match[1]].append(f"{library.name}:{member}")
    duplicates = {
        name: locations for name, locations in definitions.items() if len(locations) > 1
    }
    if duplicates:
        raise ValueError("conflicting library definitions: " + str(duplicates))
    if "_main" in definitions:
        raise ValueError("a library contains a program entry point")


def audit_programs():
    directory = ROOT / "build/userland"
    for name in json.loads((directory / "programs.json").read_text()):
        data = (directory / name).read_bytes()
        magic, cpu, _, kind, count, size, flags, _ = struct.unpack_from("<8I", data)
        if (magic, cpu, kind) != (0xFEEDFACF, 0x01000007, 2) or flags & 4:
            raise ValueError("expected a static x86_64 Mach-O program: " + name)
        position = 32
        for _ in range(count):
            command, length = struct.unpack_from("<2I", data, position)
            if length < 8 or position + length > 32 + size:
                raise ValueError("invalid Mach-O load command: " + name)
            if command in (0xE, 0xC, 0x80000018, 0x8000001F, 0x80000023):
                raise ValueError("unexpected dynamic loader dependency: " + name)
            position += length


def main():
    audit_libraries()
    audit_programs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = ROOT / "build/darwin-checks" / stamp
    directory.mkdir(parents=True)
    probe = directory / "libc-check"
    obj = compile_source(ROOT / "tests/guest/darwin_libc.c", OUT / "obj/tests/libc.o")
    libraries = [
        OUT / "lib" / name
        for name in (
            "libsystem_info_file.a",
            "libsystem_c_bootstrap.a",
            "libsystem_kernel.a",
        )
    ]
    subprocess.run(
        [
            str(LD),
            "-Z",
            "-fatal_warnings",
            "-static",
            "-arch",
            "x86_64",
            "-macosx_version_min",
            "10.11",
            "-e",
            "_start",
            "-dead_strip",
            "-no_uuid",
            "-o",
            str(probe),
            str(OUT / "obj/runtime/start-asm.o"),
            str(obj),
            *map(str, libraries),
        ],
        check=True,
    )
    image = directory / "root.hfs"
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
            "--root-image",
            str(image),
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
