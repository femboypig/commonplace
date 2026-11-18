#!/usr/bin/env python3
"""Build Apple's audit-token and code-signing entitlement task client."""

import shutil
from darwin_build import ROOT, OUT, archive, compile_source, prepare_source


def main():
    source = prepare_source("security", "OSX")
    include = OUT / "include/security"
    public = include / "Security"
    public.mkdir(parents=True, exist_ok=True)
    for library in ("codesigning", "cssm", "keychain", "authorization", "transform"):
        for header in (source / ("libsecurity_" + library) / "lib").glob("*.h"):
            shutil.copyfile(header, public / header.name)
    system = include / "System/sys"
    system.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "sources/xnu/bsd/sys/codesign.h", system / "codesign.h")
    obj = compile_source(source / "libsecurity_codesigning/lib/SecTask.c",
        OUT / "obj/security/SecTask.o", [
            "-I" + str(include),
            "-I" + str(OUT / "include/iokit-client"),
            "-idirafter", str(prepare_source("openbsm", "openbsm")),
            "-idirafter", str(prepare_source("openbsm", "openbsm") / "sys"),
            "-fblocks", "-Wno-deprecated-declarations",
        ])
    archive(OUT / "lib/libsectask.a", [obj])


if __name__ == "__main__":
    main()
