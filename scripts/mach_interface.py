"""Generate native Mach RPC bindings with the pinned MIG tool."""

import hashlib
import json
import subprocess
from darwin_build import ROOT, SDK


def generate_interface(name, definition, output, includes=()):
    output.mkdir(parents=True, exist_ok=True)
    directories = [
        ROOT / "sources/xnu/osfmk",
        ROOT / "sources/xnu/bsd",
        SDK / "usr/include",
        definition.parent,
        *includes,
    ]
    paths = {
        kind: output / (name + suffix)
        for kind, suffix in (
            ("header", ".h"),
            ("user", "User.c"),
            ("sheader", "Server.h"),
            ("server", "Server.c"),
        )
    }
    command = [
        str(ROOT / "toolchain/bin/mig"),
        "-novouchers",
        "-arch",
        "i386",
        *("-I" + str(path) for path in directories),
    ]
    for kind, path in paths.items():
        command.extend(["-" + kind, str(path)])
    command.append(str(definition))
    fingerprint = hashlib.sha256(json.dumps(command).encode())
    fingerprint.update((ROOT / "toolchain/bin/mig").read_bytes())
    fingerprint.update((ROOT / "toolchain/libexec/migcom").read_bytes())
    for directory in directories:
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix in (".h", ".defs"):
                fingerprint.update(str(path).encode())
                fingerprint.update(path.read_bytes())
    stamp = output / ("." + name + ".sha256")
    signature = fingerprint.hexdigest()
    if not (
        stamp.exists()
        and stamp.read_text() == signature
        and all(path.is_file() for path in paths.values())
    ):
        subprocess.run(command, check=True)
        stamp.write_text(signature)
    return paths
