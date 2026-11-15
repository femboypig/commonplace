#!/usr/bin/env python3
"""Build Apple's launchctl against the manager's published client protocol."""

import subprocess
from darwin_build import ROOT, OUT, LD, compile_source, prepare_source
from darwin_diagnostics import diagnostic_flags
from mach_interface import generate_interface


def main():
    source = prepare_source("launchd_manager", "launchd") / "src"
    bsm = prepare_source("openbsm", "openbsm")
    generated = OUT / "launchd-manager"
    interface = generate_interface(
        "protocol_vproc", source / "protocol_vproc.defs", generated
    )
    flags = [
        "-fblocks",
        "-fcommon",
        "-DMIG_SERVER_ROUTINE=",
        "-DOSATOMIC_USE_INLINED=1",
        "-I" + str(OUT / "include/launchd-manager"),
        "-I" + str(OUT / "include/iokit-client"),
        "-I" + str(source),
        "-I" + str(generated),
        "-I" + str(ROOT / "sources/bash/bash-3.2/lib"),
        "-I" + str(ROOT / "sources/mdns/mDNSShared"),
        "-I" + str(ROOT / "sources/iokit_user/kext.subproj"),
        "-I" + str(ROOT / "sources/xnu/libsyscall/wrappers/libproc"),
        "-idirafter",
        str(bsm),
        "-idirafter",
        str(bsm / "sys"),
        *diagnostic_flags(),
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
    ]
    objects = [
        compile_source(source / name, OUT / "obj/launchctl" / (name + ".o"), flags)
        for name in ("launchctl.c", "libbootstrap.c", "libvproc.c", "liblaunch.c")
    ]
    objects.append(
        compile_source(
            interface["user"], OUT / "obj/launchctl/protocol_vprocUser.o", flags
        )
    )
    libraries = [
        OUT / "lib/libIOKit.a",
        OUT / "lib/libbsm.a",
        OUT / "lib/libdns_sd.a",
        OUT / "bash/lib/readline/libreadline.a",
        OUT / "bash/lib/termcap/libtermcap.a",
        OUT / "system/CoreFoundation",
        OUT / "system/libSystem.B.dylib",
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
            str(OUT / "bin/launchctl"),
            *map(str, objects),
            *map(str, libraries),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
