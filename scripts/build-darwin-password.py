#!/usr/bin/env python3
"""Build the native password hash provider from the pinned OpenSSL algorithm."""

import subprocess
from darwin_build import ROOT, OUT, LD, compile_source, prepare_source
from password_sources import sha_crypt


def main():
    source = prepare_source("openssl")
    generated = OUT / "derived/password-sha-crypt.c"
    generated.parent.mkdir(parents=True, exist_ok=True)
    contents = sha_crypt((source / "apps/passwd.c").read_text())
    if not generated.exists() or generated.read_text() != contents:
        generated.write_text(contents)
    flags = ["-I" + str(OUT / "openssl/include"), "-I" + str(source / "include")]
    objects = [
        compile_source(path, OUT / "obj/password" / (path.stem + ".o"), flags)
        for path in (generated, ROOT / "userland/darwin/password/crypt.c")
    ]
    exports = OUT / "derived/password.exports"
    exports.write_text("_crypt\n_commonplace_password_verify\n")
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
            "/usr/lib/libcrypt.dylib",
            "-exported_symbols_list",
            str(exports),
            "-dead_strip",
            "-no_uuid",
            "-o",
            str(OUT / "system/libcrypt.dylib"),
            *map(str, objects),
            str(OUT / "openssl/libcrypto.a"),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
