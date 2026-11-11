#!/usr/bin/env python3
"""Build Apple's C library for the single-threaded static bootstrap profile."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from darwin_build import ROOT, OUT, compile_source, archive, prepare_source

# These facilities need the dynamic libSystem runtime or other frameworks.
EXCLUDED = {
    "stdlib/FreeBSD/abort.c",
    "stdlib/FreeBSD/psort.c",
    "stdlib/FreeBSD/psort_b.c",
    "stdlib/FreeBSD/psort_r.c",
    "gen/FreeBSD/assert.c",
    "gen/FreeBSD/daemon.c",
    "gen/FreeBSD/timezone.c",
    "gen/FreeBSD/readpassphrase.c",
    "gen/FreeBSD/scandir_b.c",
    "stdio/FreeBSD/vfwprintf.c",
    "gdtoa/FreeBSD/gdtoa-strtoIg.c",
    "gdtoa/FreeBSD/machdep_ldisQ.c",
    "gdtoa/FreeBSD/machdep_ldisd.c",
    "gdtoa/FreeBSD/machdep_ldisdd.c",
    "stdtime/FreeBSD/time32.c",
}
PATTERNS = (
    "posix1e/*.c",
    "string/**/*.c",
    "stdio/*.c",
    "stdio/FreeBSD/*.c",
    "stdlib/FreeBSD/*.c",
    "gen/FreeBSD/*.c",
    "locale/*.c",
    "locale/FreeBSD/*.c",
    "stdtime/FreeBSD/*.c",
    "regex/TRE/lib/*.c",
    "stdlib/NetBSD/*.c",
    "stdlib/OpenBSD/*.c",
    "gdtoa/FreeBSD/*.c",
)


def main():
    source = prepare_source("libc")
    platform = prepare_source("libplatform")
    bash = prepare_source("bash")
    directories = (
        "fbsdcompat",
        "locale",
        "locale/FreeBSD",
        "stdio",
        "stdio/FreeBSD",
        "stdlib/FreeBSD",
        "darwin",
        "gdtoa",
        "gdtoa/FreeBSD",
        "include",
        "stdtime/FreeBSD",
        "regex/TRE",
        "regex/TRE/lib",
        "regex/FreeBSD",
        "uuid",
        "uuid/uuidsrc",
    )
    flags = ["-I" + str(source / path) for path in directories]
    flags += [
        "-include",
        str(source / "fbsdcompat/_fbsd_compat_.h"),
        "-include",
        str(ROOT / "userland/darwin/runtime/profile.h"),
        "-include",
        str(source / "gen/__dirent.h"),
        "-D_LIBC_NO_FEATURE_VERIFICATION",
        "-DVARIANT_CANCELABLE",
        "-DVARIANT_STATIC=1",
        "-DOSATOMIC_USE_INLINED=1",
        "-D__DARWIN_NON_CANCELABLE=0",
        "-DPRIVATE",
        "-D__LIBC__",
        "-Wno-expansion-to-defined",
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
        "-Wno-incompatible-library-redeclaration",
    ]
    paths = sorted(
        {
            path
            for pattern in PATTERNS
            for path in source.glob(pattern)
            if str(path.relative_to(source)) not in EXCLUDED
            and not path.name.endswith("_b.c")
        }
    )
    paths += [
        source / path
        for path in (
            "gen/errlst.c",
            "sys/crt_externs.c",
            "gen/sigsetops.c",
            "gen/dirfd.c",
            "gen/nanosleep.c",
            "util/mkpath_np.c",
            "emulated/lutimes.c",
            "gen/devname.c",
            "gen/uname.c",
            "gen/get_compat.c",
            "sys/gettimeofday.c",
            "sys/settimeofday.c",
            "stdtime/timezone_unix03.c",
            "gen/fts.c",
            "gen/filesec.c",
            "gen/strtofflags.c",
            "emulated/lchmod.c",
            "emulated/lchflags.c",
            "sys/statx_np.c",
            "sys/openx_np.c",
            "sys/chmodx_np.c",
            "sys/umaskx_np.c",
            "sys/sigaction.c",
            "sys/fork.c",
            "sys/posix_spawn.c",
            "regex/FreeBSD/regerror.c",
        )
    ]

    def compile(path):
        output = OUT / "obj/libc" / path.relative_to(source).with_suffix(".o")
        relative = str(path.relative_to(source))
        extra = ["-DHAVE_CONFIG_H"] if "regex/TRE/" in relative else []
        if relative == "stdlib/FreeBSD/system.c":
            extra.append("-UVARIANT_CANCELABLE")
        return compile_source(path, output, [*flags, *extra])

    with ThreadPoolExecutor(max_workers=2) as pool:
        objects = list(pool.map(compile, paths))
    for name in ("qsort_b-fbsd.c", "FreeBSD/heapsort_b.c"):
        objects.append(
            compile_source(
                source / "stdlib" / name,
                OUT / "obj/libc/stdlib" / name.replace(".c", ".o"),
                [*flags, "-fblocks"],
            )
        )
    for path in sorted((platform / "src/string/generic").glob("*.c")):
        objects.append(
            compile_source(
                path,
                OUT / "obj/platform" / path.with_suffix(".o").name,
                ["-DVARIANT_STATIC=1"],
            )
        )
    for name in (
        "clear.c",
        "compare.c",
        "copy.c",
        "isnull.c",
        "pack.c",
        "unpack.c",
        "parse.c",
        "unparse.c",
    ):
        objects.append(
            compile_source(
                source / "uuid/uuidsrc" / name,
                OUT / "obj/uuid" / Path(name).with_suffix(".o"),
                ["-include", str(source / "uuid/uuid-config.h")],
            )
        )
    objects.append(
        compile_source(
            ROOT / "sources/libutil/humanize_number.c",
            OUT / "obj/libutil/humanize_number.o",
        )
    )
    for name in ("xmm_misc.c", "nan.c", "nanl.c", "floor.s", "fenv.c"):
        extra = ["-x", "assembler-with-cpp"] if name.endswith(".s") else []
        objects.append(
            compile_source(
                ROOT / "sources/libm/Source/Intel" / name,
                OUT / "obj/math" / Path(name).with_suffix(".o"),
                extra,
            )
        )
    objects.append(
        compile_source(
            ROOT / "sources/libm/Source/Intel/fenv.c",
            OUT / "obj/math/fenv_legacy.o",
            ["-DBUILDING_FOR_CARBONCORE_LEGACY"],
        )
    )
    for name in ("_sigtramp.s", "_setjmp.s", "setjmp.s"):
        objects.append(
            compile_source(
                platform / "src/setjmp/x86_64" / name,
                OUT / "obj/platform" / Path(name).with_suffix(".o"),
                ["-x", "assembler-with-cpp", "-DPRIVATE"],
            )
        )
    objects.append(
        compile_source(
            platform / "src/setjmp/generic/sigtramp.c",
            OUT / "obj/platform/sigtramp.o",
            ["-DPRIVATE"],
        )
    )
    for path in sorted((ROOT / "userland/darwin/runtime").glob("*.c")):
        if path.name == "accounts.c":
            continue
        objects.append(
            compile_source(
                path,
                OUT / "obj/runtime" / path.with_suffix(".o").name,
                [
                    "-I" + str(source / "darwin"),
                    "-DOSATOMIC_USE_INLINED=1",
                    "-Wno-deprecated-declarations",
                ],
            )
        )
    allocator = bash / "bash-3.2/lib/malloc/malloc.c"
    objects.append(
        compile_source(
            allocator,
            OUT / "obj/runtime/bash-malloc.o",
            [
                "-I" + str(ROOT / "sources/bash/bash-3.2"),
                "-include",
                str(ROOT / "sources/bash/config.h"),
                "-include",
                "stdlib.h",
                "-DHAVE_DECL_SBRK=1",
                "-Wno-deprecated-non-prototype",
                "-Wno-deprecated-declarations",
            ],
        )
    )
    objects.append(
        compile_source(
            ROOT / "userland/darwin/runtime/start.S", OUT / "obj/runtime/start-asm.o"
        )
    )
    archive(OUT / "lib/libsystem_c_bootstrap.a", objects)
    manifest = {
        "profile": "single-threaded-static",
        "source_files": [str(p.relative_to(source)) for p in paths],
    }
    (OUT / "libc-build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Darwin static C library: " + str(OUT / "lib/libsystem_c_bootstrap.a"))


if __name__ == "__main__":
    main()
