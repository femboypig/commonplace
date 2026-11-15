#!/usr/bin/env python3
"""Build Apple's launchd bootstrap and process-management clients."""

from darwin_build import ROOT, OUT, compile_source, archive, prepare_source

from mach_interface import generate_interface

from darwin_diagnostics import diagnostic_flags


def main():
    source = prepare_source("launchd")
    generated = OUT / "launch"
    generated.mkdir(parents=True, exist_ok=True)
    generate_interface("helper", source / "src/helper.defs", generated)
    flags = [
        "-fblocks",
        *diagnostic_flags(),
        "-DOSATOMIC_USE_INLINED=1",
        "-DMIG_SERVER_ROUTINE=",
        "-I" + str(source / "liblaunch"),
        "-I" + str(source / "src"),
        "-I" + str(generated),
        "-I" + str(ROOT / "sources/libc"),
        "-I" + str(ROOT / "sources/xnu/libsyscall/wrappers/libproc"),
        "-Wno-deprecated-declarations",
    ]
    objects = [
        compile_source(
            source / "liblaunch" / name,
            OUT / "obj/launch" / (name + ".o"),
            flags,
        )
        for name in ("libvproc.c", "liblaunch.c")
    ]
    objects.extend(
        compile_source(
            generated / name,
            OUT / "obj/launch" / (name + ".o"),
            flags,
        )
        for name in ("helperUser.c", "helperServer.c")
    )
    archive(OUT / "lib/libsystem_launch.a", objects)


if __name__ == "__main__":
    main()
