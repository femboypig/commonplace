#!/usr/bin/env python3
"""Build Apple's pthread implementation against the Darwin source SDK."""

from darwin_build import ROOT, OUT, compile_source, archive, prepare_source


def main():
    source = prepare_source("libpthread")
    flags = [
        "-fPIC",
        "-D__DYNAMIC__=1",
        "-I" + str(source),
        "-I" + str(source / "src"),
        "-I" + str(source / "private"),
        "-iquote" + str(source / "pthread"),
        "-I" + str(source / "os"),
        "-I" + str(ROOT / "sources/libsystem"),
        "-I" + str(ROOT / "sources/libplatform/internal"),
        "-I" + str(ROOT / "sources/xnu/libsyscall"),
        "-D__LIBC__",
        "-D__PTHREAD_BUILDING_PTHREAD__=1",
        "-D__DARWIN_UNIX03=1",
        "-D__DARWIN_64_BIT_INO_T=1",
        "-D__DARWIN_NON_CANCELABLE=1",
        "-D__DARWIN_VERS_1050=1",
        "-DOSATOMIC_USE_INLINED=1",
        "-DPRIVATE",
        "-fblocks",
        "-Wno-int-conversion",
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
    ]
    names = (
        "pthread.c",
        "pthread_tsd.c",
        "pthread_atfork.c",
        "pthread_mutex.c",
        "pthread_cond.c",
        "pthread_rwlock.c",
        "pthread_cancelable.c",
        "pthread_support.c",
        "qos.c",
        "thread_setup.c",
    )
    objects = [
        compile_source(
            source / "src" / name,
            OUT / "obj/pthread" / name.replace(".c", ".o"),
            [
                *flags,
                *(
                    [
                        "-Dmalloc=__pthread_allocator_malloc",
                        "-Dfree=__pthread_allocator_free",
                    ]
                    if name == "pthread.c"
                    else []
                ),
            ],
        )
        for name in names
    ]
    objects.append(
        compile_source(
            source / "src/pthread_asm.s",
            OUT / "obj/pthread/pthread_asm.o",
            ["-x", "assembler-with-cpp", *flags],
        )
    )
    objects.append(
        compile_source(
            source / "src/pthread_cancelable.c",
            OUT / "obj/pthread/pthread_cancelable-unix03.o",
            [
                *flags,
                "-U__DARWIN_NON_CANCELABLE",
                "-D__DARWIN_NON_CANCELABLE=0",
                "-DVARIANT_CANCELABLE",
            ],
        )
    )
    archive(OUT / "lib/libsystem_pthread.a", objects)


if __name__ == "__main__":
    main()
