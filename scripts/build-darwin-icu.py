#!/usr/bin/env python3
"""Build Apple's ICU core and internationalization code for native Darwin."""

from concurrent.futures import ThreadPoolExecutor
import shutil
import subprocess
from darwin_build import ROOT, OUT, LD, compile_source, prepare_source
from icu_build import build_host_data, source_files


def main():
    source = prepare_source("icu", "icuSources")
    data = build_host_data(source)
    flags = [
        "-DU_COMBINED_IMPLEMENTATION=1",
        "-DU_DISABLE_RENAMING=1",
        "-DU_HAVE_ATOMIC=1",
        '-DU_ICU_DATA_DEFAULT_DIR="/usr/share/icu"',
        "-fvisibility=hidden",
        "-I" + str(source / "common"),
        "-I" + str(source / "i18n"),
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
    ]
    cxx = [
        "-std=gnu++11",
        "-nostdinc++",
        "-I" + str(prepare_source("libcxx") / "include"),
    ]

    def compile(path):
        relative = path.relative_to(source)
        return compile_source(
            path,
            OUT / "obj/icu" / relative.with_suffix(".o"),
            [
                *flags,
                "-DU_"
                + ("I18N" if relative.parts[0] == "i18n" else "COMMON")
                + "_IMPLEMENTATION=1",
                *(cxx if path.suffix == ".cpp" else []),
            ],
        )

    common = source_files(source / "common")
    international = source_files(source / "i18n")
    # Check the platform and threading headers before queueing the complete build.
    initial = [p for p in common if p.stem in ("errorcode", "putil", "umutex")]
    objects = [compile(path) for path in initial]
    with ThreadPoolExecutor(max_workers=2) as pool:
        objects.extend(
            pool.map(compile, [p for p in common + international if p not in initial])
        )
    objects.append(compile(source / "stubdata/stubdata.c"))
    output = OUT / "unstripped/libicucore.A.dylib"
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(LD),
            "-L" + str(OUT / "system"),
            "-Z",
            "-fatal_warnings",
            "-arch",
            "x86_64",
            "-macosx_version_min",
            "10.11",
            "-dylib",
            "-install_name",
            "/usr/lib/libicucore.A.dylib",
            "-compatibility_version",
            "1.0.0",
            "-current_version",
            "55.1.0",
            "-dead_strip",
            "-no_uuid",
            "-o",
            str(output),
            *map(str, objects),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )
    installed = OUT / "system" / output.name
    shutil.copyfile(output, installed)
    subprocess.run(
        [
            str(ROOT / "toolchain/bin/x86_64-apple-darwin15-strip"),
            "-S",
            "-x",
            str(installed),
        ],
        check=True,
    )
    resources = OUT / "resources/icu"
    resources.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(data, resources / data.name)
    print("Darwin ICU: " + str(installed))


if __name__ == "__main__":
    main()
