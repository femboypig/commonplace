#!/usr/bin/env python3
"""Build Apple's native Mach and kqueue dispatch runtime."""

import subprocess
from darwin_build import ROOT, OUT, SDK, compile_source, archive, prepare_source


def protocol(source, output):
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(ROOT / "toolchain/bin/mig"),
            "-novouchers",
            "-arch",
            "i386",
            "-I" + str(ROOT / "sources/xnu/osfmk"),
            "-I" + str(ROOT / "sources/xnu/bsd"),
            "-I" + str(SDK / "usr/include"),
            "-DPRIVATE",
            "-header",
            str(output / "protocol.h"),
            "-user",
            str(output / "protocolUser.c"),
            "-server",
            str(output / "protocolServer.c"),
            "-sheader",
            str(output / "protocolServer.h"),
            str(source / "src/protocol.defs"),
        ],
        check=True,
    )


def main():
    source = prepare_source("libdispatch")
    generated = OUT / "dispatch"
    protocol(source, generated)
    flags = [
        "-fblocks",
        "-fcommon",
        "-fvisibility=hidden",
        "-DUSE_OBJC=0",
        "-DQOS_CLASS_LEGACY=QOS_CLASS_DEFAULT",
        "-DDISPATCH_USE_DTRACE=0",
        "-DOS_VOUCHER_ACTIVITY_SPI=1",
        "-DOS_VOUCHER_ACTIVITY_BUFFER_SPI=1",
        "-DMIG_SERVER_ROUTINE=",
        "-DPRIVATE=1",
        "-DOSATOMIC_USE_INLINED=1",
        "-I" + str(source),
        "-I" + str(source / "private"),
        "-I" + str(source / "os"),
        "-I" + str(generated),
        "-I" + str(ROOT / "sources/libpthread/private"),
        "-idirafter",
        str(ROOT / "sources/xnu/libkern"),
        "-I" + str(ROOT / "sources/xnu/libsyscall"),
        "-I" + str(ROOT / "sources/xnu/libsyscall/wrappers/libproc"),
        "-I" + str(ROOT / "sources/xnu/libsyscall/wrappers"),
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
    ]
    objects = [
        compile_source(
            source / "src" / (name + ".c"), OUT / "obj/dispatch" / (name + ".o"), flags
        )
        for name in (
            "init",
            "allocator",
            "apply",
            "benchmark",
            "data",
            "io",
            "object",
            "once",
            "queue",
            "semaphore",
            "source",
            "time",
            "transform",
            "voucher",
        )
    ]
    for name in ("protocolUser", "protocolServer"):
        objects.append(
            compile_source(
                generated / (name + ".c"), OUT / "obj/dispatch" / (name + ".o"), flags
            )
        )
    objects.append(
        compile_source(
            source / "src/block.cpp",
            OUT / "obj/dispatch/block.o",
            [
                *flags,
                "-std=gnu++11",
                "-fno-exceptions",
                "-fno-rtti",
                "-nostdinc++",
                "-I" + str(prepare_source("libcxx") / "include"),
            ],
        )
    )
    archive(OUT / "lib/libdispatch.a", objects)
    print("Darwin dispatch: " + str(OUT / "lib/libdispatch.a"))


if __name__ == "__main__":
    main()
