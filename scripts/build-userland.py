#!/usr/bin/env python3
"""Build platform programs and assemble the native Darwin userspace."""

import json
import hashlib
import re
import shutil
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build/userland"
SYSCALLS = (
    "exit",
    "fork",
    "read",
    "write",
    "open",
    "close",
    "wait4",
    "unlink",
    "chdir",
    "getpid",
    "getuid",
    "sync",
    "kill",
    "dup",
    "pipe",
    "sigaction",
    "ioctl",
    "execve",
    "dup2",
    "fcntl",
    "select",
    "mkdir",
    "rmdir",
    "setsid",
    "mount",
    "sysctl",
    "getdirentries64",
    "gettimeofday",
    "unmount",
    "reboot",
    "sigreturn",
    "fstat64",
    "ftruncate",
    "rename",
    "utimes",
    "fchmod",
    "fsync",
)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    master = (ROOT / "sources/xnu/bsd/kern/syscalls.master").read_text()
    entries = []
    for name in SYSCALLS:
        match = re.search(r"^(\d+)\s+[^\n]*\b" + name + r"\(", master, re.M)
        if not match:
            raise ValueError("missing syscall: " + name)
        entries.append(f"#define SYS_{name} {match[1]}\n")
    (OUT / "syscall-numbers.h").write_text("".join(entries))
    library = ROOT / "userland/lib"
    common = sorted(library.glob("*.c")) + sorted(library.glob("*.S"))
    programs = {"init": sorted((ROOT / "userland/init").glob("*.c"))}
    # These programs implement commonplace's boot and platform policy.
    for name in ("poweroff", "reboot"):
        programs[name] = [ROOT / "userland/bin" / f"{name}.c"]
    objects = {}
    for source in sorted(
        set(common + [path for paths in programs.values() for path in paths])
    ):
        output = OUT / "obj" / source.relative_to(ROOT / "userland").with_suffix(".o")
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                str(ROOT / "toolchain/bin/x86_64-apple-darwin15-clang"),
                "-std=c11",
                "-O2",
                "-g",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-ffreestanding",
                "-fno-builtin",
                "-fno-stack-protector",
                "-fno-pic",
                "-fno-pie",
                "-I" + str(ROOT / "userland/include"),
                "-I" + str(OUT),
                "-c",
                str(source),
                "-o",
                str(output),
            ],
            check=True,
        )
        objects[source] = output
    for name, sources in programs.items():
        subprocess.run(
            [
                str(ROOT / "toolchain/bin/x86_64-apple-darwin15-ld"),
                "-Z",
                "-fatal_warnings",
                "-static",
                "-arch",
                "x86_64",
                "-macosx_version_min",
                "10.11",
                "-e",
                "_start",
                "-no_uuid",
                "-o",
                str(OUT / name),
                *[str(objects[source]) for source in common + sources],
            ],
            check=True,
        )
    native = json.loads((ROOT / "build/darwin/commands.json").read_text())
    native["newfs_hfs"] = json.loads((ROOT / "build/darwin/newfs.json").read_text())
    for name in (*native, "bash"):
        shutil.copyfile(ROOT / "build/darwin/bin" / name, OUT / name)
    aliases = {
        "sh": "bash",
        "[": "test",
        "whoami": "id",
        "groups": "id",
        "od": "hexdump",
    }
    for name, original in aliases.items():
        shutil.copyfile(OUT / original, OUT / name)
    names = [*programs, *native, "bash", *aliases]
    (OUT / "programs.json").write_text(json.dumps(names, indent=2) + "\n")
    manifest = {
        "schema": 1,
        "profile": "native-dynamic",
        "allocator": "apple libmalloc zones",
        "native_commands": native,
        "aliases": aliases,
        "system_libraries": {
            name: hashlib.sha256(
                (ROOT / "build/darwin/system" / name).read_bytes()
            ).hexdigest()
            for name in (
                "dyld",
                "libSystem.B.dylib",
                "libsystem_kernel.dylib",
                "libpam.2.dylib",
            )
        },
        "pam_modules": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "build/darwin/pam").glob("*.so"))
        },
        "platform_commands": list(programs),
        "sources": json.loads((ROOT / "sources.lock.json").read_text()),
        "sha256": {
            name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
            for name in names
        },
    }
    (OUT / "build.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
