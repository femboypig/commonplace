#!/usr/bin/env python3
"""Verify the installed Apple IOKit framework through native kernel clients."""

from darwin_build import ROOT, OUT
from guest_probe import run_probe


def main():
    directory = run_probe("iokit", ROOT / "tests/guest/iokit_runtime.c",
        rb"native IOKit framework, registry and trap checks passed",
        flags=["-I" + str(OUT / "include/iokit-client"), "-fblocks",
            "-Wall", "-Wextra", "-Werror"],
        libraries=[OUT / "system/IOKit", OUT / "system/CoreFoundation"])
    print("native IOKit framework passed; evidence: " + str(directory), flush=True)


if __name__ == "__main__":
    main()
