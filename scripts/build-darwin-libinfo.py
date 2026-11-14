#!/usr/bin/env python3
"""Build local account lookups using Apple's Libinfo file parser and data model."""

import libinfo_sources
from darwin_build import ROOT, OUT, compile_source, archive, prepare_source


def main():
    source = prepare_source("libinfo")
    directory = source / "lookup.subproj"
    flags = [
        "-I" + str(directory),
        "-fPIC",
        "-D__DYNAMIC__=1",
        "-include",
        "stdbool.h",
        "-DOSATOMIC_USE_INLINED=1",
        "-Wno-deprecated-declarations",
    ]
    objects = [
        compile_source(
            directory / name, OUT / "obj/libinfo" / name.replace(".c", ".o"), flags
        )
        for name in ("file_module.c", "si_data.c", "ils.c", "thread_data.c")
    ]
    objects.append(
        compile_source(
            source / "membership.subproj/membership.c",
            OUT / "obj/libinfo/membership.o",
            flags,
        )
    )
    objects.append(
        compile_source(
            ROOT / "userland/darwin/libinfo/accounts.c",
            OUT / "obj/libinfo/accounts.o",
            flags,
        )
    )
    original = (directory / "libinfo.c").read_text()
    network = (directory / "si_getaddrinfo.c").read_text()
    for name in (
        "account_names",
        "group_list",
        "filesystem",
        "hosts",
        "account_reentrant",
    ):
        derived = OUT / "derived" / (name + ".c")
        derived.parent.mkdir(parents=True, exist_ok=True)
        contents = getattr(libinfo_sources, name)(original, network)
        if not derived.exists() or derived.read_text() != contents:
            derived.write_text(contents)
        objects.append(
            compile_source(derived, OUT / "obj/libinfo" / (name + ".o"), flags)
        )
    for name in ("getifaddrs", "if_nametoindex"):
        objects.append(
            compile_source(
                source / "gen.subproj" / (name + ".c"),
                OUT / "obj/libinfo" / (name + ".o"),
                flags,
            )
        )
    archive(OUT / "lib/libsystem_info_file.a", objects)
    print("Darwin local account library: " + str(OUT / "lib/libsystem_info_file.a"))


if __name__ == "__main__":
    main()
