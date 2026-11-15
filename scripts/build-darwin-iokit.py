#!/usr/bin/env python3
"""Build Apple's C IOKit clients with the native 64-bit kernel protocol."""

import shutil
from darwin_build import ROOT, OUT, compile_source, archive, prepare_source
from mach_interface import generate_interface


def main():
    source = prepare_source("iokit_user")
    private = OUT / "include/iokit-client"
    (private / "IOKit").mkdir(parents=True, exist_ok=True)
    (private / "System/libkern").mkdir(parents=True, exist_ok=True)
    for name in ("MacTypes.h", "ConditionalMacros.h", "AssertMacros.h", "Endian.h"):
        shutil.copyfile(ROOT / "sources/carbon_headers" / name, private / name)
    for name in (
        "IOKitLib.h",
        "IOKitLibPrivate.h",
        "IOCFSerialize.h",
        "IOCFUnserialize.h",
        "IOMIGMachPort.h",
    ):
        shutil.copyfile(source / name, private / "IOKit" / name)
    shutil.copyfile(
        ROOT / "sources/xnu/iokit/IOKit/IOKitKeysPrivate.h",
        private / "IOKit/IOKitKeysPrivate.h",
    )
    shutil.copyfile(
        ROOT / "sources/xnu/libkern/libkern/OSSerializeBinary.h",
        private / "System/libkern/OSSerializeBinary.h",
    )
    generated = OUT / "iokit"
    interface = generate_interface(
        "iokitmig64",
        source / "iokitmig.defs",
        generated,
        arch="x86_64",
        defines=("__LP64__", "IOKIT=1"),
    )
    flags = [
        "-DIOKIT=1",
        "-DDEPLOYMENT_TARGET_MACOSX=1",
        "-fblocks",
        "-include",
        "CoreFoundation/CFMachPort.h",
        "-I" + str(private),
        "-I" + str(generated),
        "-I" + str(source),
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
    ]
    paths = [
        source / name
        for name in (
            "IOKitLib.c",
            "IOCFSerialize.c",
            "IOCFUnserialize.tab.c",
            "IOMIGMachPort.c",
        )
    ]
    paths.append(interface["user"])
    objects = [
        compile_source(path, OUT / "obj/iokit" / (path.name + ".o"), flags)
        for path in paths
    ]
    archive(OUT / "lib/libIOKit.a", objects)


if __name__ == "__main__":
    main()
