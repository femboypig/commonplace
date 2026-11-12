#!/usr/bin/env python3
"""Build native platform synchronization and allocation-free diagnostics."""

from darwin_build import ROOT, OUT, compile_source, archive, prepare_source


def main():
    source = prepare_source("libplatform")
    flags = [
        "-fPIC",
        "-D__DYNAMIC__=1",
        "-I" + str(source / "internal"),
        "-I" + str(source / "src/os"),
        "-I" + str(ROOT / "sources/xnu/libsyscall"),
        "-DVARIANT_NO_RESOLVERS=1",
        "-DOSATOMIC_USE_INLINED=1",
        "-DOSSPINLOCK_USE_INLINED=0",
        "-DPRIVATE",
        "-Wno-int-conversion",
        "-Wno-deprecated-declarations",
    ]
    names = (
        "src/os/lock.c",
        "src/os/semaphore.c",
        "src/os/alloc_once.c",
        "src/init.c",
        "src/atomics/init.c",
        "src/simple/string_io.c",
        "src/simple/asl.c",
        "src/simple/getenv.c",
    )
    objects = [
        compile_source(
            source / name,
            OUT / "obj/platform-native" / name.replace("/", "-").replace(".c", ".o"),
            flags,
        )
        for name in names
    ]
    objects.append(
        compile_source(
            ROOT / "userland/darwin/platform/once.c",
            OUT / "obj/platform-native/once.o",
            flags,
        )
    )
    objects.append(
        compile_source(
            source / "src/atomics/x86_64/OSAtomic.s",
            OUT / "obj/platform-native/OSAtomic.o",
            [*flags, "-x", "assembler-with-cpp"],
        )
    )
    objects.append(
        compile_source(
            source / "src/atomics/x86_64/pfz.s",
            OUT / "obj/platform-native/pfz.o",
            [*flags, "-x", "assembler-with-cpp"],
        )
    )
    archive(OUT / "lib/libsystem_platform.a", objects)


if __name__ == "__main__":
    main()
