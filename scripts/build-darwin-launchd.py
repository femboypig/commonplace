#!/usr/bin/env python3
"""Build the published Apple launchd manager with its matching Mach interfaces."""

import subprocess
import shutil
from darwin_build import ROOT, OUT, LD, compile_source, prepare_source
from mach_interface import generate_interface
from darwin_diagnostics import diagnostic_flags


def main():
    source = prepare_source("launchd_manager", "launchd") / "src"
    bsm = prepare_source("openbsm", "openbsm")
    private = OUT / "include/launchd-manager"
    (private / "Security").mkdir(parents=True, exist_ok=True)
    for name in ("MacTypes.h", "ConditionalMacros.h"):
        shutil.copyfile(ROOT / "sources/carbon_headers" / name, private / name)
    for name in ("AuthSession.h", "Authorization.h"):
        shutil.copyfile(
            ROOT / "sources/security_headers/libsecurity_authorization/lib" / name,
            private / "Security" / name,
        )
    generated = OUT / "launchd-manager"
    interfaces = {}
    for name in (
        "protocol_vproc",
        "protocol_job_reply",
        "protocol_job_forward",
        "launchd_internal",
    ):
        interfaces[name] = generate_interface(
            name, source / (name + ".defs"), generated
        )
    for name in ("notify", "mach_exc"):
        interfaces[name] = generate_interface(
            name, ROOT / "sources/xnu/osfmk/mach" / (name + ".defs"), generated
        )
    flags = [
        "-fblocks",
        "-fcommon",
        "-DMIG_SERVER_ROUTINE=",
        "-DOSATOMIC_USE_INLINED=1",
        "-I" + str(private),
        "-I" + str(source),
        "-I" + str(generated),
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
        compile_source(
            source / name, OUT / "obj/launchd-manager" / (name + ".o"), flags
        )
        for name in (
            "launchd.c",
            "launchd_core_logic.c",
            "launchd_runtime.c",
            "launchd_unix_ipc.c",
            "launchd_runtime_kill.c",
            "launchd_ktrace.c",
            "libbootstrap.c",
            "libvproc.c",
            "liblaunch.c",
        )
    ]
    for name, interface in interfaces.items():
        kinds = (
            ("server",)
            if name in ("notify", "mach_exc")
            else ("user",)
            if name in ("protocol_job_reply", "protocol_job_forward")
            else ("user", "server")
        )
        for kind in kinds:
            path = interface[kind]
            objects.append(
                compile_source(
                    path,
                    OUT / "obj/launchd-manager" / (path.stem + ".o"),
                    [*flags, "-DPRIVATE"],
                )
            )
    output = OUT / "bin/apple-launchd"
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
            str(output),
            *map(str, objects),
            str(OUT / "lib/libbsm.a"),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
