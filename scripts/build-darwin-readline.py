#!/usr/bin/env python3
"""Build the original Apple Bash readline and termcap libraries for launchctl."""

import hashlib
import json
import shlex
import subprocess
from darwin_build import OUT, SDK, CFLAGS, prepare_source


def main():
    source = prepare_source("bash")
    configured = OUT / "bash"
    if not (configured / "config.h").is_file():
        raise SystemExit("build native Apple Bash before its readline libraries")
    flags = [
        *CFLAGS,
        "-fcommon",
        "-std=gnu89",
        "-Wno-deprecated-non-prototype",
        "-Wno-deprecated-declarations",
        "-Wno-error=incompatible-pointer-types",
    ]
    signature = hashlib.sha256(json.dumps(flags).encode())
    for path in (
        source / ".commonplace-patches.sha256",
        configured / "config.h",
        *sorted((SDK / "usr/include").rglob("*.h")),
    ):
        signature.update(str(path).encode())
        signature.update(path.read_bytes())
    stamp = OUT / "readline.sha256"
    rebuild = not stamp.exists() or stamp.read_text() != signature.hexdigest()
    for name in ("readline", "termcap"):
        directory = configured / "lib" / name
        if rebuild:
            subprocess.run(["make", "clean"], cwd=directory, check=True)
        subprocess.run(
            ["make", "-j2", "lib" + name + ".a", "CFLAGS=" + shlex.join(flags)],
            cwd=directory,
            check=True,
        )
    stamp.write_text(signature.hexdigest())


if __name__ == "__main__":
    main()
