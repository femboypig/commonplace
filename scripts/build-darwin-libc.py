#!/usr/bin/env python3
"""Build Apple's C library for the native Darwin LibSystem."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from darwin_build import ROOT, OUT, compile_source, archive, prepare_source

# These facilities need the dynamic libSystem runtime or other frameworks.
EXCLUDED = {
    "stdlib/FreeBSD/psort.c",
    "stdlib/FreeBSD/psort_b.c",
    "stdlib/FreeBSD/psort_r.c",
    "gen/FreeBSD/daemon.c",
    "gen/FreeBSD/timezone.c",
    "gen/FreeBSD/scandir_b.c",
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
    directories = (
        "fbsdcompat",
        "gen",
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
        str(source / "gen/__dirent.h"),
        "-D_LIBC_NO_FEATURE_VERIFICATION",
        "-DVARIANT_CANCELABLE",
        "-DVARIANT_STATIC=0",
        "-DOSATOMIC_USE_INLINED=1",
        "-D__DARWIN_NON_CANCELABLE=0",
        "-DPRIVATE",
        "-D__LIBC__",
        "-Wno-expansion-to-defined",
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
        "-Wno-incompatible-library-redeclaration",
    ]
    flags += [
        "-D__DYNAMIC__=1",
        "-DLIBC_NO_NOTIFY=1",
        "-I" + str(ROOT / "sources/libmalloc/src"),
        "-I" + str(ROOT / "sources/libpthread/private"),
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
            "util/login_tty.c",
            "gen/setlogin.c",
            "gen/getusershell.c",
            "gen/NetBSD/utmpx.c",
            "gen/utmpx-darwin.c",
            "emulated/lutimes.c",
            "gen/devname.c",
            "gen/getvfsbyname.c",
            "gen/getloadavg.c",
            "net/inet_pton.c",
            "net/inet_ntop.c",
            "net/FreeBSD/inet_ntoa.c",
            "net/FreeBSD/send.c",
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

    paths += [
        source / p
        for p in (
            "compat-43/sigaltstk.c",
            "gen/getttyent.c",
            "gen/thread_stack_pcs.c",
            "sys/_libc_init.c",
            "sys/_libc_fork_child.c",
            "gen/confstr.c",
            "sys/OpenBSD/stack_protector.c",
        )
    ]
    flags += ["-I" + str(ROOT / "sources/xnu/libsyscall/wrappers/libproc")]
    paths += sorted((source / "db").glob("**/*.c"))
    flags += ["-I" + str(p) for p in sorted((source / "db").glob("*/FreeBSD"))]

    def compile(path):
        output = OUT / "obj/libc-native" / path.relative_to(source).with_suffix(".o")
        relative = str(path.relative_to(source))
        extra = ["-DHAVE_CONFIG_H"] if "regex/TRE/" in relative else []
        if relative.startswith("db/"):
            extra.append("-D__DBINTERFACE_PRIVATE")
        return compile_source(path, output, [*flags, *extra])

    with ThreadPoolExecutor(max_workers=2) as pool:
        objects = list(pool.map(compile, paths))
    for name in ("gen/FreeBSD/sleep.c", "gen/nanosleep.c"):
        objects.append(
            compile_source(
                source / name,
                OUT / "obj/libc-nocancel" / name.replace(".c", ".o"),
                [
                    *flags,
                    "-UVARIANT_CANCELABLE",
                    "-U__DARWIN_NON_CANCELABLE",
                    "-D__DARWIN_NON_CANCELABLE=1",
                    "-DBUILDING_VARIANT=1",
                ],
            )
        )
    for name in ("udivti3", "udivmodti4", "umodti3", "gcc_personality_v0", "int_util"):
        objects.append(
            compile_source(
                ROOT / "sources/compiler_rt/lib/builtins" / (name + ".c"),
                OUT / "obj/compiler-rt" / (name + ".o"),
            )
        )
    for name in ("qsort_b-fbsd.c", "FreeBSD/heapsort_b.c"):
        objects.append(
            compile_source(
                source / "stdlib" / name,
                OUT / "obj/libc/stdlib" / name.replace(".c", ".o"),
                [*flags, "-fblocks"],
            )
        )
    objects.append(
        compile_source(
            source / "net/FreeBSD/recv.c",
            OUT / "obj/libc/recv.o",
            [*flags, "-DVARIANT_CANCELABLE=1"],
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
        "gen_uuid.c",
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
    objects.append(
        compile_source(
            source / "net/FreeBSD/inet_addr.c",
            OUT / "obj/net/inet_aton.o",
            flags,
        )
    )
    renames = [
        "-D" + name + "=commonplace_bsd_" + name
        for name in ("syslog", "vsyslog", "openlog", "closelog", "setlogmask")
    ]
    objects.append(
        compile_source(
            prepare_source("libc_directories", "gen") / "NSSystemDirectories.c",
            OUT / "obj/directories/NSSystemDirectories.o",
            flags,
        )
    )
    objects.append(
        compile_source(
            source / "gen/oldsyslog.c",
            OUT / "obj/syslog/bsd.o",
            [*renames, "-fvisibility=hidden", "-Wno-deprecated-non-prototype"],
        )
    )
    objects.append(
        compile_source(
            ROOT / "userland/darwin/syslog/locking.c", OUT / "obj/syslog/locking.o"
        )
    )
    objects.append(
        compile_source(
            ROOT / "sources/xnu/libsyscall/wrappers/getiopolicy_np.c",
            OUT / "obj/libc-native/getiopolicy_np.o",
            flags,
        )
    )
    library = OUT / "lib" / "libsystem_c.a"
    archive(library, objects)
    manifest = {
        "profile": "native-dynamic",
        "source_files": [str(p.relative_to(source)) for p in paths],
    }
    (OUT / "libc-build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Darwin C library: " + str(library))


if __name__ == "__main__":
    main()
