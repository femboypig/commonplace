#!/usr/bin/env python3
"""Build Apple's OpenPAM core against the native Darwin runtime."""

import re
import subprocess
from darwin_build import OUT, LD, compile_source, prepare_source


def main():
    source = prepare_source("openpam", "openpam")
    makefile = (source / "lib/Makefile.am").read_text()
    section = makefile.split("libpam_la_SOURCES", 1)[1].split("$(NULL)", 1)[0]
    names = re.findall(r"\b([a-z_]+\.c)\b", section)
    flags = [
        "-DHAVE_CONFIG_H=1",
        "-fblocks",
        "-I" + str(source),
        "-I" + str(source / "include"),
        "-I" + str(source / "lib"),
        "-Wno-deprecated-non-prototype",
    ]
    objects = [
        compile_source(
            source / "lib" / name, OUT / "obj/pam" / name.replace(".c", ".o"), flags
        )
        for name in names
    ]
    output = OUT / "system/libpam.2.dylib"
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
            "-dylib",
            "-install_name",
            "/usr/lib/libpam.2.dylib",
            "-compatibility_version",
            "1.0.0",
            "-current_version",
            "2.0.0",
            "-dead_strip",
            "-no_uuid",
            "-o",
            str(output),
            *map(str, objects),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )
    modules = OUT / "pam"
    modules.mkdir(exist_ok=True)
    upstream = prepare_source("pam_modules")
    for name, path in (
        ("pam_deny", source / "modules/pam_deny/pam_deny.c"),
        ("pam_rootok", upstream / "modules/pam_rootok/pam_rootok.c"),
        ("pam_self", upstream / "modules/pam_self/pam_self.c"),
    ):
        obj = compile_source(
            path,
            OUT / "obj/pam-modules" / (name + ".o"),
            [
                *flags,
                "-include",
                "security/pam_appl.h",
                "-include",
                "security/openpam.h",
            ],
        )
        target = modules / (name + ".so")
        dependencies = [str(OUT / "system/libSystem.B.dylib")]
        if name != "pam_deny":
            dependencies.insert(0, str(output))
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
                "-dylib",
                "-install_name",
                "/usr/lib/pam/" + target.name,
                "-no_uuid",
                "-o",
                str(target),
                str(obj),
                *dependencies,
            ],
            check=True,
        )
    print("Darwin OpenPAM: " + str(output))


if __name__ == "__main__":
    main()
