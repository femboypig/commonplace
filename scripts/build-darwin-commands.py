#!/usr/bin/env python3
"""Build pinned Apple command sources against the native Darwin LibSystem."""

import hashlib
import json
from pathlib import Path
import subprocess
from darwin_build import ROOT, OUT, LD, compile_source, prepare_source


def main():
    registry = json.loads((ROOT / "userland/darwin/commands.json").read_text())
    if registry["schema"] != 1:
        raise ValueError("unsupported command registry")
    libraries = [OUT / "lib/libsystem_file.a", OUT / "system/libSystem.B.dylib"]
    binaries = OUT / "bin"
    binaries.mkdir(parents=True, exist_ok=True)
    manifest = {}
    sources = {}
    for name, configuration in registry["programs"].items():
        if Path(name).name != name:
            raise ValueError("invalid command name: " + name)
        objects = []
        for relative in configuration["sources"]:
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("invalid source path: " + relative)
            project = path.parts[0]
            if project not in sources:
                sources[project] = prepare_source(project)
            objects.append(
                compile_source(
                    sources[project] / Path(*path.parts[1:]),
                    OUT / "obj/commands" / name / path.with_suffix(".o"),
                    [
                        "-Wno-deprecated-non-prototype",
                        "-Wno-deprecated-declarations",
                        *configuration.get("flags", []),
                    ],
                )
            )
        output = binaries / name
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
                "-dead_strip",
                "-no_uuid",
                "-o",
                str(output),
                *map(str, objects),
                *map(str, libraries),
            ],
            check=True,
        )
        manifest[name] = {
            "sources": configuration["sources"],
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        }
        print("Darwin command: " + name, flush=True)
    (OUT / "commands.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
