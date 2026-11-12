#!/usr/bin/env python3
"""Cross-build Apple's Mach-O dynamic loader from pinned sources."""

import subprocess
from darwin_build import ROOT, OUT, LD, compile_source, archive, prepare_source


def main():
    source = prepare_source("dyld")
    flags = [
        "-I" + str(source / "include"),
        "-I" + str(source / "include/mach-o"),
        "-I" + str(ROOT / "sources/cctools/cctools/include"),
        "-I" + str(source / "src"),
        "-I" + str(source / "launch-cache"),
        "-I" + str(prepare_source("libcxx") / "include"),
        "-I" + str(ROOT / "sources/libcxxabi/include"),
        "-DDYLD_VERSION=360.22",
        "-DDYLD_SHARED_CACHE_SUPPORT=0",
        "-Wno-c++11-narrowing",
        "-Wno-deprecated-declarations",
        "-Wno-int-conversion",
    ]
    names = (
        "dyldStartup.s",
        "dyldInitialization.cpp",
        "dyld.cpp",
        "dyldAPIs.cpp",
        "dyldExceptions.c",
        "dyld_gdb.cpp",
        "glue.c",
        "ImageLoader.cpp",
        "ImageLoaderMachO.cpp",
        "stub_binding_helper.s",
        "dyldNew.cpp",
        "ImageLoaderMachOClassic.cpp",
        "ImageLoaderMachOCompressed.cpp",
    )
    objects = []
    for name in names:
        extra = ["-x", "assembler-with-cpp"] if name.endswith(".s") else []
        if name.endswith(".cpp"):
            extra = ["-std=gnu++11", "-nostdinc++", "-fno-rtti"]
        objects.append(
            compile_source(
                source / "src" / name,
                OUT / "obj/dyld" / (name + ".o"),
                [*flags, *extra, "-fPIC", "-D__DYNAMIC__=1"],
            )
        )
    loader_objects = objects
    names = (
        "dyldAPIsInLibSystem.cpp",
        "dyldLibSystemGlue.c",
        "dyldLock.cpp",
        "threadLocalVariables.c",
        "threadLocalHelpers.s",
        "dyld_stub_binder.s",
        "start_glue.s",
    )
    objects = []
    for name in names:
        extra = ["-x", "assembler-with-cpp"] if name.endswith(".s") else []
        if name.endswith(".cpp"):
            extra = ["-std=gnu++11", "-nostdinc++"]
        objects.append(
            compile_source(
                source / "src" / name,
                OUT / "obj/libdyld" / (name + ".o"),
                [*flags, *extra, "-fPIC", "-D__DYNAMIC__=1", "-fblocks"],
            )
        )
    archive(OUT / "lib/libdyld.a", objects)

    link_loader(loader_objects)


def link_loader(loader_objects):
    unwind = prepare_source("libunwind")
    objects = []
    for name in (
        "libuwind.cxx",
        "UnwindLevel1.c",
        "UnwindLevel1-gcc-ext.c",
        "Registers.s",
        "unw_getcontext.s",
    ):
        flags = [
            "-DFOR_DYLD=1",
            "-DNDEBUG=1",
            "-fPIC",
            "-I" + str(unwind / "include"),
            "-I" + str(prepare_source("libcxx") / "include"),
            "-I" + str(ROOT / "sources/libcxxabi/include"),
        ]
        if name.endswith(".s"):
            flags += ["-x", "assembler-with-cpp"]
        elif name.endswith(".cxx"):
            flags += ["-std=gnu++11", "-nostdinc++"]
        objects.append(
            compile_source(
                unwind / "src" / name, OUT / "obj/unwind-dyld" / (name + ".o"), flags
            )
        )
    version = OUT / "derived/dyld_version.c"
    version.parent.mkdir(parents=True, exist_ok=True)
    (OUT / "system").mkdir(parents=True, exist_ok=True)
    content = 'double dyldVersionNumber = 360.22;\nconst unsigned char dyldVersionString[] = "@(#)program:dyld project:dyld-360.22";\n'
    if not version.exists() or version.read_text() != content:
        version.write_text(content)
    objects.append(compile_source(version, OUT / "obj/dyld-version.o", ["-fPIC"]))
    command = [
        str(LD),
        "-Z",
        "-fatal_warnings",
        "-dylinker",
        "-arch",
        "x86_64",
        "-macosx_version_min",
        "10.11",
        "-dylinker_install_name",
        "/usr/lib/dyld",
        "-seg1addr",
        "0x7fff5fc00000",
        "-e",
        "__dyld_start",
        "-exported_symbols_list",
        str(ROOT / "sources/dyld/src/dyld.exp"),
        "-dead_strip",
        "-no_uuid",
        "-no_warn_inits",
        "-o",
        str(OUT / "system/dyld"),
    ]
    command += list(map(str, loader_objects))
    command += list(map(str, objects))
    command += [
        str(OUT / "lib" / name)
        for name in (
            "libsystem_c.a",
            "libsystem_mach.a",
            "libsystem_kernel_native.a",
            "libsystem_pthread.a",
            "libsystem_platform.a",
            "libcxx.a",
            "libcxxabi.a",
        )
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
