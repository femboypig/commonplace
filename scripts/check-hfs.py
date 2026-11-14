#!/usr/bin/env python3
"""Exercise Apple's HFS verifier and repairer on isolated, damaged volumes."""

from datetime import datetime, timezone
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from darwin_build import ROOT, OUT, LD, compile_source
from rootfs_image import build_image


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def case(name, command, expected):
    return {"name": name, "send": command + "\n", "expect": expected}


def boot(directory, recovery, system, scratch, cases, disk_root=False):
    directory.mkdir()
    scenario = directory / "cases.json"
    scenario.write_text(json.dumps(cases, indent=2) + "\n")
    command = [
        sys.executable,
        str(ROOT / "scripts/boot-qemu.py"),
        "--seconds",
        "240",
        "--memory",
        "1024",
        "--system-disk",
        str(system),
        "--disk-image",
        str(scratch),
        "--check-console",
        "--console-case-file",
        str(scenario),
        "--expect-shutdown",
        "poweroff",
        "--output",
        str(directory),
    ]
    command += ["--disk-root"] if disk_root else ["--root-image", str(recovery)]
    with (directory / "output.log").open("w") as output:
        subprocess.run(command, check=True, stdout=output, stderr=subprocess.STDOUT)
    result = json.loads((directory / "diagnostics.json").read_text())
    return result["console"]["passed"]


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = ROOT / "build/hfs-checks" / stamp
    directory.mkdir(parents=True)
    system = directory / "system.hfs"
    recovery = directory / "recovery.hfs"
    scratch = directory / "scratch.raw"
    build_image(system, size_mib=64, persistent=True)
    shutil.copyfile(ROOT / "build/rootfs/root.hfs", recovery)
    with scratch.open("wb") as stream:
        stream.truncate(16 * 1024 * 1024)
    obj = compile_source(ROOT / "tests/guest/raw_disk.c", OUT / "obj/tests/raw-disk.o")
    probe = directory / "raw-disk-check"
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
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run(
        [hfs, str(recovery), "add", str(probe), "/bin/raw-disk-check"], check=True
    )
    subprocess.run(
        [hfs, str(recovery), "chmod", "755", "/bin/raw-disk-check"], check=True
    )
    token = directory / "token"
    token.write_text("hfs-repair-preserved-" + stamp + "\n")
    subprocess.run(
        [hfs, str(system), "add", str(token), "/root/repair-token"], check=True
    )
    clean_hash = digest(system)
    phases = [
        boot(
            directory / "clean",
            recovery,
            system,
            scratch,
            [
                case(
                    "raw disk interface",
                    "raw-disk-check",
                    r"\nraw disk: transfer, alignment, bounds and device isolation passed\n",
                ),
                case(
                    "native filesystem identification",
                    "fstyp_hfs /dev/cp1; echo recognized:$?",
                    r"\nrecognized:1\n",
                ),
                case(
                    "clean filesystem verification",
                    "fsck_hfs -fn -c 16m /dev/cp1; echo check:$?",
                    r"appears to be OK[\s\S]*\ncheck:0\n",
                ),
            ],
        )
    ]
    if digest(system) != clean_hash:
        raise ValueError("read-only verification changed the system volume")
    with system.open("r+b") as stream:
        stream.seek(1024)
        header = stream.read(512)
        journal_block = struct.unpack_from(">I", header, 12)[0]
        block_size = struct.unpack_from(">I", header, 40)[0]
        journal_offset = journal_block * block_size
        stream.seek(journal_offset)
        journal = stream.read(512)
        flags = struct.unpack_from(">I", journal)[0]
        stream.seek(journal_offset)
        stream.write(struct.pack(">I", (flags & ~1) | 2))
    external_hash = digest(system)
    phases.append(
        boot(
            directory / "external-journal",
            recovery,
            system,
            scratch,
            [
                case(
                    "reject unsupported external journal verification",
                    "fsck_hfs -fn -c 16m /dev/rcp1; echo external:$?",
                    r"External HFS journals require IOMedia UUID services[\s\S]*\nexternal:8\n",
                ),
                case(
                    "reject unsupported external journal repair",
                    "fsck_hfs -fy -c 16m /dev/rcp1; echo external:$?",
                    r"External HFS journals require IOMedia UUID services[\s\S]*\nexternal:8\n",
                ),
            ],
        )
    )
    if digest(system) != external_hash:
        raise ValueError("unsupported external journal check changed the volume")
    with system.open("r+b") as stream:
        stream.seek(journal_offset)
        stream.write(journal)
    original_free = None
    with system.open("r+b") as stream:
        for offset in (1024, system.stat().st_size - 1024):
            stream.seek(offset)
            header = bytearray(stream.read(512))
            if header[:2] != b"H+":
                raise ValueError("missing HFS+ volume header")
            free = struct.unpack_from(">I", header, 48)[0]
            if original_free is None:
                original_free = free
            struct.pack_into(">I", header, 48, free - 1)
            stream.seek(offset)
            stream.write(header)
    damaged_hash = digest(system)
    phases.append(
        boot(
            directory / "detect",
            recovery,
            system,
            scratch,
            [
                case(
                    "detect inconsistent allocation count",
                    "fsck_hfs -fn -c 16m /dev/rcp1; echo check:$?",
                    r"[Ii]nvalid volume free block count[\s\S]*\ncheck:8\n",
                ),
            ],
        )
    )
    if digest(system) != damaged_hash:
        raise ValueError("read-only error detection changed the damaged volume")
    phases.append(
        boot(
            directory / "repair",
            recovery,
            system,
            scratch,
            [
                case(
                    "repair allocation metadata",
                    "fsck_hfs -fy -c 16m /dev/rcp1; echo repair:$?",
                    r"[Rr]epair[\s\S]*\nrepair:0\n",
                ),
                case(
                    "verify repaired volume",
                    "fsck_hfs -fn -c 16m /dev/rcp1; echo check:$?",
                    r"appears to be OK[\s\S]*\ncheck:0\n",
                ),
            ],
        )
    )
    with system.open("rb") as stream:
        for offset in (1024, system.stat().st_size - 1024):
            stream.seek(offset + 48)
            if struct.unpack(">I", stream.read(4))[0] != original_free:
                raise ValueError("repair did not restore both volume headers")
    phases.append(
        boot(
            directory / "boot-repaired",
            recovery,
            system,
            scratch,
            [
                case(
                    "preserved file after repair",
                    "cat /root/repair-token",
                    r"\nhfs-repair-preserved-" + stamp + r"\n",
                ),
                case(
                    "mounted volume write protection",
                    "fsck_hfs -fy -c 16m /dev/rcp1; echo mounted:$?",
                    r"mounted with write access[\s\S]*\nmounted:8\n",
                ),
            ],
            disk_root=True,
        )
    )
    summary = {
        "passed": True,
        "phases": len(phases),
        "console_checks": sum(phases),
        "original_free_blocks": original_free,
    }
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        "native HFS detection, repair and raw disk checks passed; evidence: "
        + str(directory)
    )


if __name__ == "__main__":
    main()
