#!/usr/bin/env python3
"""Build Apple's Mach-O architecture and image-section accessors."""

from darwin_build import ROOT, OUT, compile_source, archive


def main():
    source = ROOT / "sources/cctools/cctools"
    objects = [
        compile_source(
            source / "libmacho" / name,
            OUT / "obj/macho" / (name + ".o"),
            [
                "-I" + str(source / "include"),
                "-D__CCTOOLS_DEPRECATED2=",
                "-Wno-deprecated-declarations",
            ],
        )
        for name in (
            "arch.c",
            "getsecbyname.c",
            "getsegbyname.c",
            "swap.c",
            "i386_swap.c",
        )
    ]
    archive(OUT / "lib/libsystem_macho.a", objects)


if __name__ == "__main__":
    main()
