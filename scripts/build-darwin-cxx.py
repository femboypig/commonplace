#!/usr/bin/env python3
"""Build the source C++ support needed by Darwin's dynamic loader."""

from darwin_build import ROOT, OUT, compile_source, archive, prepare_source


def main():
    flags = [
        "-std=gnu++11",
        "-nostdinc++",
        "-I" + str(prepare_source("libcxx") / "include"),
        "-I" + str(ROOT / "sources/libcxxabi/include"),
        "-I" + str(ROOT / "sources/libunwind/include"),
        "-I" + str(ROOT / "sources/libunwind/src"),
        "-D_LIBCPP_BUILDING_LIBRARY",
        "-DLIBCXXABI_BAREMETAL=0",
        "-DNDEBUG=1",
        "-fPIC",
        "-Wno-deprecated-declarations",
        "-Wno-int-conversion",
    ]
    projects = {
        "libcxx": [
            "algorithm.cpp",
            "exception.cpp",
            "stdexcept.cpp",
            "string.cpp",
            "new.cpp",
        ],
        "libcxxabi": [
            "abort_message.cpp",
            "cxa_aux_runtime.cpp",
            "cxa_default_handlers.cpp",
            "cxa_new_delete.cpp",
            "cxa_demangle.cpp",
            "exception.cpp",
            "cxa_exception.cpp",
            "cxa_exception_storage.cpp",
            "cxa_guard.cpp",
            "cxa_handlers.cpp",
            "cxa_personality.cpp",
            "cxa_vector.cpp",
            "cxa_virtual.cpp",
            "private_typeinfo.cpp",
            "stdexcept.cpp",
            "typeinfo.cpp",
        ],
        "libunwind": [
            "libuwind.cxx",
            "UnwindLevel1.c",
            "UnwindLevel1-gcc-ext.c",
            "Registers.s",
            "unw_getcontext.s",
        ],
    }
    for name, names in projects.items():
        source = prepare_source(name)
        objects = []
        for filename in names:
            extra = []
            if filename.endswith(".s"):
                extra = ["-x", "assembler-with-cpp"]
            elif filename.endswith(".c"):
                extra = ["-std=gnu11"]
            objects.append(
                compile_source(
                    source / "src" / filename,
                    OUT / "obj" / name / (filename + ".o"),
                    [*flags, *extra],
                )
            )
        archive(OUT / "lib" / (name + ".a"), objects)


if __name__ == "__main__":
    main()
