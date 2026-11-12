#!/usr/bin/env python3
"""Link the native console LibSystem and its block runtime."""

import subprocess
from darwin_build import ROOT, OUT, LD, compile_source, archive, prepare_source


def main():
    blocks = prepare_source("libclosure")
    flags = [
        "-fPIC",
        "-D__DYNAMIC__=1",
        "-fblocks",
        "-I" + str(blocks),
        "-include",
        "TargetConditionals.h",
        "-Wno-deprecated-declarations",
    ]
    objects = [
        compile_source(
            blocks / name, OUT / "obj/blocks" / name.replace(".c", ".o"), flags
        )
        for name in ("runtime.c", "data.c")
    ]
    archive(OUT / "lib/libsystem_blocks.a", objects)
    source = prepare_source("libsystem")
    init = compile_source(
        source / "init.c",
        OUT / "obj/libsystem/init.o",
        [
            "-fPIC",
            "-D__DYNAMIC__=1",
            "-I" + str(ROOT / "sources/libc/darwin"),
            "-I" + str(ROOT / "sources/xnu/libsyscall"),
            "-I" + str(ROOT / "sources/xnu/libsyscall/wrappers"),
            "-Wno-int-conversion",
        ],
    )
    output = OUT / "system/libSystem.B.dylib"
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(LD),
        "-Z",
        "-fatal_warnings",
        "-dylib",
        "-arch",
        "x86_64",
        "-macosx_version_min",
        "10.11",
        "-install_name",
        "/usr/lib/libSystem.B.dylib",
        "-current_version",
        "1226.10.1",
        "-compatibility_version",
        "1.0.0",
        "-not_for_dyld_shared_cache",
        "-dead_strip",
        "-no_warn_inits",
        "-no_uuid",
        "-o",
        str(output),
        str(init),
        str(
            compile_source(
                prepare_source("keymgr") / "keymgr.c",
                OUT / "obj/keymgr/keymgr.o",
                [
                    "-fPIC",
                    "-D__DYNAMIC__=1",
                    "-DOSATOMIC_USE_INLINED=1",
                    "-Wno-deprecated-declarations",
                ],
            )
        ),
    ]
    for name in (
        "libsystem_info_file.a",
        "libsystem_c.a",
        "libsystem_malloc.a",
        "libsystem_pthread.a",
        "libsystem_platform.a",
        "libdyld.a",
        "libsystem_blocks.a",
        "libunwind.a",
    ):
        command += ["-force_load", str(OUT / "lib" / name)]
    command += [str(OUT / "lib" / name) for name in ("libcxx.a", "libcxxabi.a")]
    command += ["-reexport_library", str(OUT / "system/libsystem_kernel.dylib")]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
