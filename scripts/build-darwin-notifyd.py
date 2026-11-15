#!/usr/bin/env python3
"""Build Apple's system notification daemon and its matching MIG server."""

import subprocess
from darwin_build import OUT, LD, compile_source, prepare_source
from darwin_diagnostics import diagnostic_flags
from mach_interface import generate_interface


def main():
    source = prepare_source("libnotify")
    bsm = prepare_source("openbsm", "openbsm")
    generated = OUT / "notify"
    interface = generate_interface("notify_ipc", source / "notify_ipc.defs", generated)
    flags = [
        "-fblocks",
        "-fcommon",
        "-DOSATOMIC_USE_INLINED=1",
        "-DMIG_SERVER_ROUTINE=",
        "-I" + str(source),
        "-I" + str(source / "notifyd"),
        "-I" + str(generated),
        "-idirafter",
        str(bsm),
        "-idirafter",
        str(bsm / "sys"),
        *diagnostic_flags(),
        "-Wno-deprecated-declarations",
    ]
    paths = [
        source / "notifyd" / name
        for name in (
            "notifyd.c",
            "notify_proc.c",
            "service.c",
            "timer.c",
            "pathwatch.c",
        )
    ]
    paths.append(interface["server"])
    objects = [
        compile_source(path, OUT / "obj/notifyd" / (path.name + ".o"), flags)
        for path in paths
    ]
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
            str(OUT / "bin/notifyd"),
            *map(str, objects),
            str(OUT / "lib/libbsm.a"),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
