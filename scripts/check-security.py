#!/usr/bin/env python3
"""Verify Apple's task identity client against live XNU audit tokens."""

from darwin_build import ROOT, OUT
from guest_probe import run_probe


def main():
    directory = run_probe("security", ROOT / "tests/guest/security_task.c",
        rb"native security task identity and entitlement checks passed",
        flags=["-I" + str(OUT / "include/security"),
            "-fblocks", "-Wall", "-Wextra", "-Werror"],
        libraries=[OUT / "lib/libsectask.a", OUT / "lib/libbsm.a",
            OUT / "system/CoreFoundation"])
    print("native security task checks passed; evidence: " + str(directory), flush=True)


if __name__ == "__main__":
    main()
