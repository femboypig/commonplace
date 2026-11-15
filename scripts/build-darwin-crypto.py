#!/usr/bin/env python3
"""Build a private native OpenSSL crypto archive for password hashing."""

import hashlib
import json
import os
import shlex
import subprocess
from darwin_build import ROOT, OUT, SDK, CC, AR, CFLAGS, prepare_source


def main():
    source = prepare_source("openssl")
    directory = OUT / "openssl"
    directory.mkdir(parents=True, exist_ok=True)
    command = [
        "perl",
        str(source / "Configure"),
        "darwin64-x86_64-cc",
        "no-asm",
        "no-shared",
        "no-threads",
        "no-dso",
        "no-engine",
        "no-module",
        "no-tests",
        "no-apps",
        "no-docs",
        "no-legacy",
        "no-autoload-config",
        "--with-rand-seed=devrandom",
    ]
    environment = {
        "CC": str(CC),
        "AR": str(AR),
        "RANLIB": str(ROOT / "toolchain/bin/x86_64-apple-darwin15-ranlib"),
        "CFLAGS": shlex.join([*CFLAGS, "-Wno-deprecated-declarations"]),
    }
    signature = hashlib.sha256(
        json.dumps([command, environment], sort_keys=True).encode()
    )
    for path in (
        source / ".commonplace-patches.sha256",
        CC,
        *sorted((SDK / "usr/include").rglob("*.h")),
    ):
        signature.update(str(path).encode())
        signature.update(path.read_bytes())
    stamp = directory / "configure.sha256"
    if not stamp.exists() or stamp.read_text() != signature.hexdigest():
        if (directory / "Makefile").exists():
            subprocess.run(["make", "clean"], cwd=directory, check=True)
        subprocess.run(
            command, cwd=directory, env={**os.environ, **environment}, check=True
        )
        stamp.write_text(signature.hexdigest())
    subprocess.run(
        ["make", "-j2", "build_generated", "libcrypto.a"],
        cwd=directory,
        env={**os.environ, **environment},
        check=True,
    )


if __name__ == "__main__":
    main()
