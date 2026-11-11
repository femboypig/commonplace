#!/usr/bin/env python3
"""Build Apple's file copying and removal libraries for the static profile."""

from darwin_build import ROOT, OUT, compile_source, archive, prepare_source


def main():
    objects = []
    for project in ("copyfile", "removefile"):
        source = prepare_source(project)
        for path in sorted(source.glob("*.c")):
            objects.append(
                compile_source(
                    path,
                    OUT / "obj" / project / path.with_suffix(".o").name,
                    [
                        "-DPRIVATE",
                        "-DVARIANT_STATIC=1",
                        "-fblocks",
                        "-Wno-deprecated-declarations",
                        "-Wno-deprecated-non-prototype",
                        "-I" + str(source),
                    ],
                )
            )
    blocks = ROOT / "sources/compiler_rt/lib/BlocksRuntime"
    config = OUT / "derived/blocks/config.h"
    config.parent.mkdir(parents=True, exist_ok=True)
    contents = "#define HAVE_SYNC_BOOL_COMPARE_AND_SWAP_INT 1\n#define HAVE_SYNC_BOOL_COMPARE_AND_SWAP_LONG 1\n"
    if not config.exists() or config.read_text() != contents:
        config.write_text(contents)
    for name in ("data.c", "runtime.c"):
        objects.append(
            compile_source(
                blocks / name,
                OUT / "obj/blocks" / name.replace(".c", ".o"),
                ["-I" + str(config.parent)],
            )
        )
    archive(OUT / "lib/libsystem_file.a", objects)
    print("Darwin file libraries: " + str(OUT / "lib/libsystem_file.a"))


if __name__ == "__main__":
    main()
