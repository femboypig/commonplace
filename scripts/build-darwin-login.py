#!/usr/bin/env python3
"""Build Apple's PAM login and console provisioning policy."""

from darwin_build import ROOT, OUT, compile_source, prepare_source, link_program


def main():
    source = prepare_source("system_cmds") / "login.tproj/login.c"
    obj = compile_source(
        source,
        OUT / "obj/login/login.o",
        [
            "-DUSE_PAM=1",
            "-fblocks",
            "-Wno-deprecated-declarations",
            "-Wno-deprecated-non-prototype",
        ],
    )
    link_program(OUT / "bin/login", [obj], [OUT / "system/libpam.2.dylib"])
    first = compile_source(
        ROOT / "userland/darwin/services/first_login.c", OUT / "obj/login/first-login.o"
    )
    link_program(OUT / "bin/first-login", [first])


if __name__ == "__main__":
    main()
