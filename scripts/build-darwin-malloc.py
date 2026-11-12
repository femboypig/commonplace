#!/usr/bin/env python3
"""Build Apple's malloc zones, magazine allocator and heap diagnostics."""

import re
from darwin_build import ROOT, OUT, compile_source, archive, prepare_source


def main():
    source = prepare_source("libmalloc")
    generated = OUT / "malloc-derived"
    generated.mkdir(parents=True, exist_ok=True)
    probes = (source / "src/magmallocProvider.d").read_text()
    definitions = ["/* DTrace is disabled for this target. */\n"]
    for name in re.findall(r"probe\s+(\w+)\s*\(", probes):
        macro = "MAGMALLOC_" + name.upper()
        definitions += [
            f"#define {macro}(...) ((void)0)\n",
            f"#define {macro}_ENABLED() 0\n",
        ]
    header = generated / "magmallocProvider.h"
    contents = "".join(definitions)
    if not header.exists() or header.read_text() != contents:
        header.write_text(contents)
    flags = [
        "-fPIC",
        "-D__DYNAMIC__=1",
        "-I" + str(source / "include/malloc"),
        "-I" + str(source / "src"),
        "-I" + str(generated),
        "-I" + str(ROOT / "sources/xnu/libsyscall"),
        "-DPRIVATE",
        "-fblocks",
        "-DOSATOMIC_USE_INLINED=1",
        "-Wno-int-conversion",
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
    ]
    names = (
        "malloc.c",
        "magazine_malloc.c",
        "nano_malloc.c",
        "bitarray.c",
        "stack_logging.c",
        "stack_logging_disk.c",
    )
    objects = [
        compile_source(
            source / "src" / name, OUT / "obj/malloc" / name.replace(".c", ".o"), flags
        )
        for name in names
    ]
    archive(OUT / "lib/libsystem_malloc.a", objects)


if __name__ == "__main__":
    main()
