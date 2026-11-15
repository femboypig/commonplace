#!/usr/bin/env python3
"""Build Apple's bootstrap namespace RPC clients from launchd."""

from darwin_build import OUT, compile_source, archive, prepare_source
from mach_interface import generate_interface


def main():
    source = prepare_source("launchd")
    generated = OUT / "launch"
    interface = generate_interface("job", source / "src/job.defs", generated)
    flags = [
        "-fblocks",
        "-DMIG_SERVER_ROUTINE=",
        "-DOSATOMIC_USE_INLINED=1",
        "-I" + str(source / "src"),
        "-I" + str(source / "liblaunch"),
        "-I" + str(generated),
        "-Wno-deprecated-declarations",
    ]
    objects = [
        compile_source(
            source / "liblaunch/libbootstrap.c", OUT / "obj/launch/bootstrap.o", flags
        ),
        compile_source(interface["user"], OUT / "obj/launch/jobUser.o", flags),
    ]
    archive(OUT / "lib/libsystem_bootstrap.a", objects)


if __name__ == "__main__":
    main()
