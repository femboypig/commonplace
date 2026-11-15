#!/usr/bin/env python3
"""Populate an HFS+ system or RAM recovery root without mounting it."""

import json
import hashlib
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def system_files():
    names = json.loads((ROOT / "build/userland/programs.json").read_text())
    system_programs = {
        "init": "launchd",
        "fsck_hfs": "fsck_hfs",
        "fstyp_hfs": "fstyp_hfs",
        "mount_hfs": "mount_hfs",
        "newfs_hfs": "newfs_hfs",
    }
    programs = {
        (
            "/sbin/" + system_programs[name]
            if name in system_programs
            else "/bin/" + name
        ): ROOT / "build/userland" / name
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
    for name, target in (
        ("login", "/usr/bin/login"),
        ("passwd", "/usr/bin/passwd"),
        ("vipw", "/usr/sbin/vipw"),
        ("pwd_mkdb", "/usr/sbin/pwd_mkdb"),
    ):
        programs[target] = ROOT / "build/darwin/bin" / name
    programs["/usr/lib/libcrypt.dylib"] = ROOT / "build/darwin/system/libcrypt.dylib"
    programs["/usr/lib/libpam.2.dylib"] = ROOT / "build/darwin/system/libpam.2.dylib"
    for name in (
        "pam_deny",
        "pam_rootok",
        "pam_self",
        "pam_unix",
        "pam_nologin",
        "pam_uwtmp",
    ):
        programs["/usr/lib/pam/" + name + ".so"] = (
            ROOT / "build/darwin/pam" / (name + ".so")
        )
    programs["/usr/lib/libicucore.A.dylib"] = (
        ROOT / "build/darwin/system/libicucore.A.dylib"
    )
    programs[
        "/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation"
    ] = ROOT / "build/darwin/system/CoreFoundation"
    programs.update(system_resources())
    return programs


def system_resources():
    return {
        "/usr/share/icu/icudt55l.dat": ROOT / "build/darwin/resources/icu/icudt55l.dat",
        "/System/Library/Frameworks/CoreFoundation.framework/Versions/A/Resources/Info.plist": ROOT
        / "build/darwin/resources/CoreFoundation/Info.plist",
    }


def system_symlinks():
    framework = "/System/Library/Frameworks/CoreFoundation.framework/"
    return {
        framework + path: target
        for path, target in (
            ("Versions/Current", "A"),
            ("CoreFoundation", "Versions/Current/CoreFoundation"),
            ("Resources", "Versions/Current/Resources"),
        )
    }


def build_image(image, size_mib=64, persistent=False):
    image = Path(image)
    image.parent.mkdir(parents=True, exist_ok=True)
    formatter = ROOT / "toolchain/bin/newfs_hfs"
    hfs = ROOT / "toolchain/bin/hfsplus"
    programs = system_files()
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
        directories = {
            "/dev",
            "/etc/pam.d",
            "/tmp",
            "/root",
            "/data",
            "/usr/bin",
            "/usr/sbin",
            "/var/log",
            "/var/run",
        }
        for path in (*programs, *directories):
            directories.update(
                str(parent) for parent in Path(path).parents if str(parent) != "/"
            )
        for directory in sorted(
            directories, key=lambda path: (len(Path(path).parts), path)
        ):
            subprocess.run([str(hfs), str(image), "mkdir", directory], check=True)
        hashes = {}
        for destination, program in programs.items():
            subprocess.run(
                [str(hfs), str(image), "add", str(program), destination], check=True
            )
            subprocess.run(
                [
                    str(hfs),
                    str(image),
                    "chmod",
                    "644"
                    if destination in system_resources()
                    else ("4755" if destination == "/usr/bin/passwd" else "755"),
                    destination,
                ],
                check=True,
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
        for path, target in system_symlinks().items():
            subprocess.run([str(hfs), str(image), "symlink", path, target], check=True)
        for configuration in sorted((ROOT / "userland/darwin/etc").rglob("*")):
            if not configuration.is_file():
                continue
            destination = "/etc/" + str(
                configuration.relative_to(ROOT / "userland/darwin/etc")
            )
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
        subprocess.run([str(hfs), str(image), "chmod", "700", "/root"], check=True)
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
