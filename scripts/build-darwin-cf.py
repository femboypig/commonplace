#!/usr/bin/env python3
"""Build Apple's published CoreFoundation C runtime on native Darwin."""

from concurrent.futures import ThreadPoolExecutor
import shutil
import subprocess
from darwin_build import ROOT, OUT, LD, compile_source, prepare_source


def main():
    source = prepare_source("cf")
    icu = prepare_source("icu", "icuSources")
    flags = [
        "-fblocks",
        "-fcommon",
        "-fexceptions",
        "-fconstant-cfstrings",
        "-DCF_BUILDING_CF=1",
        "-DDEPLOYMENT_TARGET_MACOSX=1",
        "-DINCLUDE_OBJC=0",
        "-DVERSION=1153.18",
        "-DU_SHOW_DRAFT_API=1",
        "-DU_SHOW_CPLUSPLUS_API=0",
        "-DU_DISABLE_RENAMING=1",
        "-DOSATOMIC_USE_INLINED=1",
        "-include",
        str(source / "CoreFoundation_Prefix.h"),
        "-idirafter",
        str(source),
        "-I" + str(icu / "common"),
        "-I" + str(icu / "i18n"),
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
    ]

    def compile(path):
        return compile_source(
            path, OUT / "obj/cf" / path.with_suffix(".o").name, [*flags, "-x", "c"]
        )

    initial = [source / name for name in ("CFBase.c", "CFRuntime.c", "CFRunLoop.c")]
    objects = [compile(path) for path in initial]
    paths = [
        path
        for path in sorted(source.glob("*.c"))
        if path not in initial and path.name != "plconvert.c"
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        objects.extend(pool.map(compile, paths))
    output = OUT / "unstripped/CoreFoundation"
    output.parent.mkdir(parents=True, exist_ok=True)
    sections = []
    for name, file in (
        ("__csbitmaps", "CFCharacterSetBitmaps.bitmap"),
        ("__properties", "CFUniCharPropertyDatabase.data"),
        ("__data", "CFUnicodeData-L.mapping"),
    ):
        sections += ["-sectcreate", "__UNICODE", name, str(source / file)]
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
            "/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation",
            "-compatibility_version",
            "150.0.0",
            "-current_version",
            "1153.18",
            "-no_uuid",
            "-dead_strip",
            "-no_warn_inits",
            "-init",
            "___CFInitialize",
            "-alias_list",
            str(source / "SymbolAliases"),
            *sections,
            "-segprot",
            "__UNICODE",
            "r",
            "r",
            "-o",
            str(output),
            *map(str, objects),
            str(OUT / "system/libicucore.A.dylib"),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )
    installed = OUT / "system/CoreFoundation"
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
    resources = OUT / "resources/CoreFoundation"
    resources.mkdir(parents=True, exist_ok=True)
    info = (source / "Info.plist").read_text()
    info = info.replace("$(EXECUTABLE_NAME)", "CoreFoundation").replace(
        "$(CURRENT_PROJECT_VERSION)", "1153.18"
    )
    (resources / "Info.plist").write_text(info)
    print("Darwin CoreFoundation: " + str(installed))


if __name__ == "__main__":
    main()
