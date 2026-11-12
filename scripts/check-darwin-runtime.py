#!/usr/bin/env python3
"""Exercise native loading, allocation and pthreads in an isolated QEMU image."""

from datetime import datetime, timezone
import argparse
import json
import shutil
import subprocess
import sys
from darwin_build import ROOT, OUT, LD, compile_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory", type=int, default=1024)
    options = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = ROOT / "build/runtime-checks" / stamp
    directory.mkdir(parents=True)
    library = OUT / "system/libSystem.B.dylib"
    binaries = {}
    for name, source, flags in (
        ("runtime-check", "darwin_runtime.c", ["-e", "_main"]),
        (
            "runtime-plugin.dylib",
            "darwin_runtime_plugin.c",
            ["-dylib", "-install_name", "/usr/lib/runtime-plugin.dylib"],
        ),
    ):
        obj = compile_source(
            ROOT / "tests/guest" / source, OUT / "obj/tests" / (source + ".o")
        )
        output = directory / name
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
                "-no_warn_inits",
                "-no_uuid",
                *flags,
                "-o",
                str(output),
                str(obj),
                str(library),
            ],
            check=True,
        )
        binaries[
            "/bin/runtime-check" if name == "runtime-check" else "/usr/lib/" + name
        ] = output
    image = directory / "root.hfs"
    shutil.copyfile(ROOT / "build/rootfs/root.hfs", image)
    hfs = ROOT / "toolchain/bin/hfsplus"
    # Keep the root and data disk of an interactive guest outside this test.
    for target, source in binaries.items():
        subprocess.run([str(hfs), str(image), "add", str(source), target], check=True)
        subprocess.run([str(hfs), str(image), "chmod", "755", target], check=True)
    cases = directory / "cases.json"
    cases.write_text(
        json.dumps(
            [
                {
                    "name": "native runtime stress",
                    "send": "runtime-check; echo runtime-status:$?\n",
                    "expect": r"darwin runtime: syscall cancellation, cleanup and once recovery passed[\s\S]*runtime-status:0",
                }
            ],
            indent=2,
        )
        + "\n"
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/boot-qemu.py"),
            "--seconds",
            "180",
            "--memory",
            str(options.memory),
            "--root-image",
            str(image),
            "--check-console",
            "--console-case-file",
            str(cases),
            "--output",
            str(directory / "boot"),
        ],
        check=True,
    )
    print("native Darwin runtime checks passed; evidence: " + str(directory))


if __name__ == "__main__":
    main()
