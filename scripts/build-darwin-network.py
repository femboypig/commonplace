#!/usr/bin/env python3
"""Build the userspace bridge to Apple's network interface registration API."""

from darwin_build import ROOT, OUT, compile_source, link_program


def main():
    obj = compile_source(ROOT / "userland/darwin/network/register.c",
        OUT / "obj/network/register.o", [
            "-I" + str(OUT / "include/iokit-client"),
            "-I" + str(ROOT / "sources/ionetwork"),
            "-fblocks", "-Wall", "-Wextra", "-Werror",
        ])
    link_program(OUT / "bin/register-network", [obj], [
        OUT / "lib/libIOKit.a", OUT / "system/CoreFoundation",
    ])


if __name__ == "__main__":
    main()
