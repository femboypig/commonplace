#!/usr/bin/env python3
"""Build Apple's HFS formatter with XNU's canonical Unicode implementation."""

import hashlib
import json
import subprocess
from darwin_build import ROOT, OUT, LD, compile_source, prepare_source


def main():
    source = prepare_source("hfs")
    vfs = prepare_source("xnu", "bsd/vfs", "xnu-vfs-userland")
    sha = prepare_source("xnu", "osfmk/prng/YarrowCoreLib/src", "xnu-sha1-userland")
    flags = [
        "-DCOMMONPLACE_NO_EXTERNAL_JOURNAL=1",
        "-D__APPLE_API_UNSTABLE=1",
        "-DCOMMONPLACE_UTFCONV_USERLAND=1",
        "-fblocks",
        "-I" + str(sha),
        "-I" + str(ROOT / "sources/libutil"),
        "-Wno-deprecated-non-prototype",
    ]
    objects = [
        compile_source(
            source / "newfs_hfs" / name, OUT / "obj/newfs" / (name + ".o"), flags
        )
        for name in ("newfs_hfs.c", "makehfs.c", "hfs_endian.c")
    ]
    objects.append(
        compile_source(vfs / "vfs_utfconv.c", OUT / "obj/newfs/utfconv.o", flags)
    )
    objects.append(
        compile_source(
            sha / "sha1mod.c",
            OUT / "obj/newfs/sha1.o",
            [*flags, "-include", "sys/param.h"],
        )
    )
    cxx = prepare_source("libcxx")
    for name in ("wipefs.cpp", "ExtentManager.cpp"):
        objects.append(
            compile_source(
                ROOT / "sources/libutil" / name,
                OUT / "obj/newfs" / (name + ".o"),
                [
                    *flags,
                    "-std=gnu++11",
                    "-nostdinc++",
                    "-I" + str(cxx / "include"),
                    "-Wno-deprecated-declarations",
                ],
            )
        )
    output = OUT / "bin/newfs_hfs"
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
            str(OUT / "lib/libcxx.a"),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )
    manifest = {
        "sources": [
            "hfs/newfs_hfs",
            "xnu/bsd/vfs/vfs_utfconv.c",
            "xnu/osfmk/prng/YarrowCoreLib/src/sha1mod.c",
            "libutil/wipefs.cpp",
            "libutil/ExtentManager.cpp",
        ],
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    (OUT / "newfs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Darwin HFS formatter: " + str(output))


if __name__ == "__main__":
    main()
