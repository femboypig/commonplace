#!/usr/bin/env python3
"""Reuse XNU host tools only while their sources and output hashes match."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ("kextsymboltool", "setsegname", "decomment", "installfile", "replacecontents", "config")


def signature():
    inputs = {ROOT / "scripts/build-xnu-host.sh", Path(__file__).resolve()}
    for directory in ("build/xnu-source/SETUP", "compat/host", "sources/cctools/cctools/include"):
        inputs.update(path for path in (ROOT / directory).rglob("*")
            if path.is_file() and path.suffix in (".c", ".h", ".l", ".y"))
    inputs.update(ROOT / "build/cctools" / library for library in (
        "libmacho/.libs/libmacho.a", "libstuff/.libs/libstuff.a"))
    digest = hashlib.sha256()
    for path in sorted(inputs):
        digest.update(str(path.relative_to(ROOT)).encode() + b"\0")
        digest.update(path.read_bytes())
    for tool in ("clang", "bison", "flex"):
        digest.update(subprocess.check_output([tool, "--version"]))
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("object_root", type=Path)
    parser.add_argument("--record", action="store_true")
    options = parser.parse_args()
    directory = options.object_root / "SETUP"
    stamp = directory / "commonplace-host-tools.json"
    inputs = signature()
    outputs = {}
    for tool in TOOLS:
        path = directory / tool / tool
        if not path.is_file() or not path.stat().st_mode & 0o111:
            if options.record:
                raise ValueError("host tool output is missing: " + str(path))
            raise SystemExit(1)
        outputs[tool] = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = dict(inputs=inputs, outputs=outputs)
    if options.record:
        temporary = stamp.with_suffix(".tmp")
        temporary.write_text(json.dumps(expected, indent=2) + "\n")
        temporary.replace(stamp)
    else:
        try:
            actual = json.loads(stamp.read_text())
        except (OSError, ValueError):
            raise SystemExit(1)
        if actual != expected:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
