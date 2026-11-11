"""Shared cross-compilation settings for native Darwin userspace."""

from pathlib import Path
import subprocess
import hashlib
import json
import shlex
import shutil

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build/darwin"
SDK = ROOT / "build/darwin-sdk"
CC = ROOT / "toolchain/bin/x86_64-apple-darwin15-clang"
LD = ROOT / "toolchain/bin/x86_64-apple-darwin15-ld"
AR = ROOT / "toolchain/bin/x86_64-apple-darwin15-ar"
RESOURCE = Path(
    subprocess.check_output([str(CC), "-print-resource-dir"], text=True).strip()
)
CFLAGS = [
    "-static",
    "-fno-blocks",
    "-std=gnu11",
    "-D_FORTIFY_SOURCE=0",
    "-O2",
    "-g",
    "-ffreestanding",
    "-fno-builtin",
    "-fno-stack-protector",
    "-fno-pic",
    "-fno-pie",
    "-fno-common",
    "-nostdlibinc",
    "-isystem",
    str(SDK / "usr/include"),
    "-isystem",
    str(RESOURCE / "include"),
]


def compile_source(source, output, flags=()):
    output.parent.mkdir(parents=True, exist_ok=True)
    dependencies = output.with_suffix(".d")
    stamp = output.with_suffix(".command")
    command = [
        str(CC),
        *CFLAGS,
        *flags,
        "-MD",
        "-MF",
        str(dependencies),
        "-c",
        str(source),
        "-o",
        str(output),
    ]
    fingerprint = hashlib.sha256(json.dumps(command).encode()).hexdigest()
    if (
        output.exists()
        and dependencies.exists()
        and stamp.exists()
        and stamp.read_text() == fingerprint
    ):
        try:
            paths = shlex.split(
                dependencies.read_text().replace("\\\n", "").split(":", 1)[1]
            )
            if paths and all(
                Path(path).stat().st_mtime_ns <= output.stat().st_mtime_ns
                for path in paths
            ):
                return output
        except (OSError, ValueError, IndexError):
            pass
    subprocess.run(command, check=True)
    stamp.write_text(fingerprint)
    return output


def archive(output, objects):
    output.parent.mkdir(parents=True, exist_ok=True)
    stamp = output.with_suffix(".members.json")
    members = json.dumps(list(map(str, objects)))
    if output.exists() and stamp.exists() and stamp.read_text() == members:
        if all(
            path.stat().st_mtime_ns <= output.stat().st_mtime_ns for path in objects
        ):
            return
    temporary = output.with_suffix(".new.a")
    temporary.unlink(missing_ok=True)
    subprocess.run([str(AR), "rcs", str(temporary), *map(str, objects)], check=True)
    temporary.replace(output)
    stamp.write_text(members)


def prepare_source(name, subdirectory=None, patch_name=None):
    upstream = ROOT / "sources" / name
    destination = OUT / "source" / name
    if subdirectory:
        destination /= subdirectory
    patches = sorted((ROOT / "patches" / (patch_name or name)).glob("*.patch"))
    signature = hashlib.sha256((upstream / ".commonplace-source.json").read_bytes())
    for patch in patches:
        signature.update(patch.name.encode())
        signature.update(patch.read_bytes())
    stamp = destination / ".commonplace-patches.sha256"
    fingerprint = signature.hexdigest()
    if stamp.exists() and stamp.read_text() == fingerprint:
        return destination
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(upstream / subdirectory if subdirectory else upstream, destination)
    for patch in patches:
        subprocess.run(
            [
                "patch",
                "--batch",
                "--fuzz=0",
                "-p1",
                "-d",
                str(destination),
                "-i",
                str(patch),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    stamp.write_text(fingerprint)
    return destination
