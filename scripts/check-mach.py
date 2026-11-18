#!/usr/bin/env python3
"""Exercise Libsyscall's native Mach VM aliases above the 32-bit address space."""

from darwin_build import ROOT
from guest_probe import run_probe


def main():
    directory = run_probe("mach", ROOT / "tests/guest/mach_vm_runtime.c",
        rb"native Mach VM aliases and wide memory transfers passed",
        flags=["-Wall", "-Wextra", "-Werror"])
    print("native Mach VM checks passed; evidence: " + str(directory), flush=True)


if __name__ == "__main__":
    main()
