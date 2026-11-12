#!/usr/bin/env python3
"""Link XNU's syscall and Mach clients as the native kernel provider."""

import subprocess
import json
from darwin_build import OUT, LD, compile_source, prepare_source


def main():
    source = prepare_source("xnu", "libsyscall", "libsyscall")
    upcalls = compile_source(
        source / "wrappers/_libc_funcptr.c",
        OUT / "obj/kernel-provider/upcalls.o",
        ["-fPIC", "-DPRIVATE"],
    )
    output = OUT / "system/libsystem_kernel.dylib"
    output.parent.mkdir(parents=True, exist_ok=True)
    # The upcall wrappers are private to this provider, as in Apple's split LibSystem.
    archive_objects = json.loads((OUT / "lib/libsystem_mach.members.json").read_text())
    objects = [p for p in archive_objects if not p.endswith("/upcalls.o")]
    support = [source / "mach" / name for name in ("string.c", "fprintf_stderr.c")]
    support += sorted((source / "wrappers/string").glob("*.c"))
    objects += [
        str(
            compile_source(
                p,
                OUT / "obj/kernel-provider" / (p.stem + ".o"),
                [
                    "-fPIC",
                    "-DPRIVATE",
                    "-Wno-pointer-compare",
                    "-I" + str(source / "mach"),
                ],
            )
        )
        for p in support
    ]
    command = [
        str(LD),
        "-Z",
        "-fatal_warnings",
        "-dylib",
        "-arch",
        "x86_64",
        "-macosx_version_min",
        "10.11",
        "-install_name",
        "/usr/lib/system/libsystem_kernel.dylib",
        "-dead_strip",
        "-no_uuid",
        "-o",
        str(output),
        str(upcalls),
        *objects,
        "-force_load",
        str(OUT / "lib/libsystem_kernel_native.a"),
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
