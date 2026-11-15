#!/usr/bin/env python3
"""Build Apple's local password database and account administration tools."""

from darwin_build import ROOT, OUT, compile_source, prepare_source, link_program


def main():
    flags = [
        "-I" + str(ROOT / "userland/darwin/password"),
        "-fblocks",
        "-Wno-deprecated-declarations",
        "-Wno-deprecated-non-prototype",
    ]
    project = prepare_source("system_cmds")
    for name, paths, extra in (
        (
            "passwd",
            ("passwd.tproj/passwd.c", "passwd.tproj/file_passwd.c"),
            ["-DCOMMONPLACE_LOCAL_ACCOUNTS=1"],
        ),
        ("pwd_mkdb", ("pwd_mkdb.tproj/pwd_mkdb.c", "pwd_mkdb.tproj/pw_scan.c"), []),
        ("vipw", ("vipw.tproj/vipw.c", "vipw.tproj/pw_util.c"), []),
    ):
        objects = [
            compile_source(
                project / path,
                OUT / "obj/accounts" / name / (path.replace("/", "-") + ".o"),
                [*flags, *extra],
            )
            for path in paths
        ]
        link_program(OUT / "bin" / name, objects, [OUT / "system/libcrypt.dylib"])


if __name__ == "__main__":
    main()
