#!/usr/bin/env python3
"""Build Apple's structured logging client and persistent ASL store."""

from darwin_build import OUT, compile_source, archive, prepare_source
from mach_interface import generate_interface


def main():
    source = prepare_source("libc_asl")
    generated = OUT / "asl"
    interface = generate_interface("asl_ipc", source / "gen/asl_ipc.defs", generated)
    library = source / "gen"
    flags = [
        "-fblocks",
        "-DMIG_SERVER_ROUTINE=",
        "-DOSATOMIC_USE_INLINED=1",
        "-I" + str(library),
        "-I" + str(generated),
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
    ]
    objects = [
        compile_source(library / name, OUT / "obj/asl" / (name + ".o"), flags)
        for name in (
            "asl.c",
            "asl_core.c",
            "asl_msg.c",
            "asl_fd.c",
            "asl_file.c",
            "asl_store.c",
            "asl_legacy1.c",
            "asl_util.c",
        )
    ]
    objects.append(
        compile_source(interface["user"], OUT / "obj/asl/asl_ipcUser.o", flags)
    )
    archive(OUT / "lib/libsystem_asl.a", objects)


if __name__ == "__main__":
    main()
