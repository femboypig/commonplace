#!/usr/bin/env python3
"""Build Apple's native IORegistry inspection utility."""

from darwin_build import ROOT, OUT, compile_source, link_program, prepare_source


def main():
    source = prepare_source("iokit_tools")
    bash = prepare_source("bash") / "bash-3.2"
    obj = compile_source(source / "ioreg.tproj/ioreg.c",
        OUT / "obj/iokit-tools/ioreg.o", [
            "-I" + str(OUT / "include/iokit-client"),
            "-I" + str(bash / "lib/termcap"),
            "-DPRIVATE", "-fblocks", "-Wno-deprecated-declarations",
        ])
    link_program(OUT / "bin/ioreg", [obj], [
        OUT / "lib/libIOKit.a", OUT / "bash/lib/termcap/libtermcap.a",
        OUT / "system/CoreFoundation",
    ])


if __name__ == "__main__":
    main()
