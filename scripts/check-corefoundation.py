#!/usr/bin/env python3
"""Exercise native Apple CoreFoundation APIs in QEMU."""

from datetime import datetime, timezone
import argparse
import json
import shutil
import subprocess
import sys
from darwin_build import ROOT, OUT, LD, compile_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disk-root", action="store_true")
    options = parser.parse_args()
    directory = (
        ROOT
        / "build/cf-checks"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    directory.mkdir(parents=True)
    image = directory / ("system.hfs" if options.disk_root else "recovery.hfs")
    if options.disk_root:
        from rootfs_image import build_image

        build_image(image, 64, persistent=True)
    else:
        shutil.copyfile(ROOT / "build/rootfs/root.hfs", image)
    objects = [
        compile_source(
            ROOT / "tests/guest" / (name + ".c"),
            OUT / "obj/tests" / (name + ".o"),
            ["-fblocks", "-fconstant-cfstrings"],
        )
        for name in ("cf_values", "cf_runloop", "cf_runtime")
    ]
    probe = directory / "cf-check"
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
            "-e",
            "_main",
            "-no_uuid",
            "-o",
            str(probe),
            *map(str, objects),
            str(OUT / "system/CoreFoundation"),
            str(OUT / "system/libicucore.A.dylib"),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    subprocess.run([hfs, str(image), "add", str(probe), "/bin/cf-check"], check=True)
    subprocess.run([hfs, str(image), "chmod", "755", "/bin/cf-check"], check=True)
    cases = directory / "cases.json"
    cases.write_text(
        json.dumps(
            [
                {
                    "name": "native corefoundation",
                    "send": "cf-check; echo cf-status:$?\n",
                    "expect": r"native corefoundation passed[\s\S]*cf-status:0",
                }
            ]
        )
        + "\n"
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/boot-qemu.py"),
            *(
                ["--system-disk", str(image), "--disk-root"]
                if options.disk_root
                else ["--root-image", str(image)]
            ),
            "--seconds",
            "180",
            "--check-console",
            "--console-case-file",
            str(cases),
            "--expect-shutdown",
            "poweroff",
            "--output",
            str(directory / "boot"),
        ],
        check=True,
    )
    print("native corefoundation passed: " + str(directory))


if __name__ == "__main__":
    main()
