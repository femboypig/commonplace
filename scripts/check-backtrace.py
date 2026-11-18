#!/usr/bin/env python3
"""Check Apple's stack capture and dyld-backed symbol formatting."""

from darwin_build import ROOT
from guest_probe import run_probe


def main():
    directory = run_probe("backtrace", ROOT / "tests/guest/backtrace.c",
        rb"native backtraces and symbol formatting passed on main and worker stacks",
        flags=["-fno-omit-frame-pointer", "-Wall", "-Wextra", "-Werror"])
    print("native backtraces passed; evidence: " + str(directory), flush=True)


if __name__ == "__main__":
    main()
