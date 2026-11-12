#!/usr/bin/env python3
"""Populate an HFS+ system or RAM recovery root without mounting it."""

import json
import hashlib
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def build_image(image, size_mib=32, persistent=False):
    image = Path(image)
    image.parent.mkdir(parents=True, exist_ok=True)
    formatter = ROOT / "toolchain/bin/newfs_hfs"
    hfs = ROOT / "toolchain/bin/hfsplus"
    names = json.loads((ROOT / "build/userland/programs.json").read_text())
    programs = {
        ("/sbin/launchd" if name == "init" else "/bin/" + name): ROOT
        / "build/userland"
        / name
        for name in names
    }
    programs.update(
        {
            "/usr/lib/dyld": ROOT / "build/darwin/system/dyld",
            "/usr/lib/libSystem.B.dylib": ROOT
            / "build/darwin/system/libSystem.B.dylib",
            "/usr/lib/system/libsystem_kernel.dylib": ROOT
            / "build/darwin/system/libsystem_kernel.dylib",
        }
    )
    for artifact in (formatter, hfs, *programs.values()):
        if not artifact.is_file():
            raise SystemExit("missing rootfs input: " + str(artifact))
    with tempfile.TemporaryDirectory(
        dir=image.parent, prefix=".populate-"
    ) as temporary:
        temporary = Path(temporary)
        with image.open("wb") as output:
            output.truncate(size_mib * 1024 * 1024)
        subprocess.run(
            [
                str(formatter),
                *(["-J"] if persistent else []),
                "-v",
                "commonplace",
                "-U",
                "0",
                "-G",
                "0",
                "-M",
                "755",
                str(image),
            ],
            check=True,
        )
        for directory in (
            "dev",
            "sbin",
            "bin",
            "etc",
            "tmp",
            "root",
            "data",
            "usr",
            "usr/bin",
            "usr/sbin",
            "usr/lib",
            "usr/lib/system",
        ):
            subprocess.run([str(hfs), str(image), "mkdir", "/" + directory], check=True)
        hashes = {}
        for destination, program in programs.items():
            subprocess.run(
                [str(hfs), str(image), "add", str(program), destination], check=True
            )
            subprocess.run(
                [str(hfs), str(image), "chmod", "755", destination], check=True
            )
            extracted = temporary / "verify"
            subprocess.run(
                [str(hfs), str(image), "extract", destination, str(extracted)],
                check=True,
            )
            if extracted.read_bytes() != program.read_bytes():
                raise ValueError(
                    "HFS+ program round-trip verification failed: " + destination
                )
            hashes[destination] = hashlib.sha256(program.read_bytes()).hexdigest()
        for configuration in sorted((ROOT / "userland/darwin/etc").iterdir()):
            destination = "/etc/" + configuration.name
            subprocess.run(
                [str(hfs), str(image), "add", str(configuration), destination],
                check=True,
            )
            mode = "600" if configuration.name == "master.passwd" else "644"
            subprocess.run(
                [str(hfs), str(image), "chmod", mode, destination], check=True
            )
            hashes[destination] = hashlib.sha256(configuration.read_bytes()).hexdigest()
        subprocess.run([str(hfs), str(image), "chmod", "1777", "/tmp"], check=True)
        motd = temporary / "motd"
        motd.write_text(
            "commonplace\n"
            + (
                "Persistent system root.\n"
                if persistent
                else "RAM recovery root. Use /data for persistent files.\n"
            )
        )
        subprocess.run(
            [str(hfs), str(image), "add", str(motd), "/etc/motd"], check=True
        )
        hashes["/etc/motd"] = hashlib.sha256(motd.read_bytes()).hexdigest()
    return hashes
