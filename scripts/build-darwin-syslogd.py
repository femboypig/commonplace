#!/usr/bin/env python3
"""Build Apple's ASL and BSD system logging daemon."""

import subprocess
from darwin_build import OUT, LD, compile_source, prepare_source
from mach_interface import generate_interface


def main():
    source = prepare_source("syslog_services")
    asl = prepare_source("libc_asl")
    bsm = prepare_source("openbsm", "openbsm")
    generated = OUT / "asl"
    interface = generate_interface("asl_ipc", asl / "gen/asl_ipc.defs", generated)
    flags = [
        "-idirafter",
        str(bsm),
        "-idirafter",
        str(bsm / "sys"),
        "-fblocks",
        "-fcommon",
        "-DMIG_SERVER_ROUTINE=",
        "-DOSATOMIC_USE_INLINED=1",
        "-I" + str(source / "aslcommon"),
        "-I" + str(source / "syslogd.tproj"),
        "-I" + str(generated),
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
    ]
    paths = sorted((source / "syslogd.tproj").glob("*.c"))
    paths += [
        source / "aslcommon" / name for name in ("asl_memory.c", "asl_mini_memory.c")
    ]
    paths.append(interface["server"])
    objects = [
        compile_source(path, OUT / "obj/syslogd" / (path.name + ".o"), flags)
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
            str(OUT / "bin/syslogd"),
            *map(str, objects),
            str(OUT / "lib/libbsm.a"),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )

    utility = compile_source(
        source / "util.tproj/syslog.c", OUT / "obj/syslogd/syslog-client.o", flags
    )
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
            str(OUT / "bin/syslog"),
            str(utility),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
