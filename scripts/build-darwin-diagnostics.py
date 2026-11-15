#!/usr/bin/env python3
"""Build Apple's allocation-safe runtime diagnostics without CrashReporter."""

from darwin_build import OUT, compile_source, archive, prepare_source

from darwin_diagnostics import diagnostic_flags


def main():
    source = prepare_source("libc")
    flags = [
        "-fblocks",
        *diagnostic_flags(),
        "-I" + str(source),
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
    ]
    objects = [
        compile_source(
            source / "os" / name, OUT / "obj/diagnostics" / (name + ".o"), flags
        )
        for name in ("assumes.c", "debug_private.c")
    ]
    archive(OUT / "lib/libsystem_diagnostics.a", objects)


if __name__ == "__main__":
    main()
