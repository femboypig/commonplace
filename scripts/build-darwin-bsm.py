#!/usr/bin/env python3
"""Build Apple's OpenBSM audit client against the native Darwin ABI."""

import hashlib
import json
import os
import shlex
import subprocess
from darwin_build import (
    OUT,
    SDK,
    CC,
    LD,
    CFLAGS,
    compile_source,
    archive,
    prepare_source,
)


def main():
    source = prepare_source("openbsm", "openbsm")
    configured = OUT / "bsm"
    configured.mkdir(parents=True, exist_ok=True)
    includes = ["-idirafter", str(source), "-idirafter", str(source / "sys")]
    environment = {
        "CC": str(CC),
        "CFLAGS": shlex.join([flag for flag in CFLAGS if flag != "-g"]),
        "CPPFLAGS": shlex.join(includes),
        "LDFLAGS": shlex.join(
            [
                "-nostdlib",
                "-fuse-ld=" + str(LD),
                "-Wl,-e,_main",
                "-L" + str(OUT / "system"),
            ]
        ),
        "LIBS": str(OUT / "system/libSystem.B.dylib"),
        "ac_cv_file__usr_include_mach_audit_triggers_defs": "yes"
        if (SDK / "usr/include/mach/audit_triggers.defs").is_file()
        else "no",
    }
    command = [
        "bash",
        str(source / "configure"),
        "--host=x86_64-apple-darwin15",
        "--build=x86_64-pc-linux-gnu",
        "--disable-shared",
        "--enable-static",
        "--with-native-includes",
    ]
    signature = hashlib.sha256(
        json.dumps([command, environment], sort_keys=True).encode()
    )
    for path in (
        source / ".commonplace-patches.sha256",
        CC,
        LD,
        OUT / "system/libSystem.B.dylib",
        *sorted((SDK / "usr/include").rglob("*.h")),
    ):
        signature.update(str(path).encode())
        signature.update(path.read_bytes())
    stamp = configured / "configure.sha256"
    if not stamp.exists() or stamp.read_text() != signature.hexdigest():
        subprocess.run(
            command, cwd=configured, env={**os.environ, **environment}, check=True
        )
        stamp.write_text(signature.hexdigest())
    objects = [
        compile_source(
            path,
            OUT / "obj/bsm" / path.with_suffix(".o").name,
            [
                "-I" + str(configured),
                *includes,
                "-Wno-deprecated-non-prototype",
                "-Wno-deprecated-declarations",
            ],
        )
        for path in sorted((source / "libbsm").glob("*.c"))
    ]
    archive(OUT / "lib/libbsm.a", objects)


if __name__ == "__main__":
    main()
