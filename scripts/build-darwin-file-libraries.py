#!/usr/bin/env python3
"""Build Apple's file copying and removal libraries for the static profile."""

from darwin_build import OUT, compile_source, archive, prepare_source


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
    archive(OUT / "lib/libsystem_file.a", objects)
    print("Darwin file libraries: " + str(OUT / "lib/libsystem_file.a"))


if __name__ == "__main__":
    main()
