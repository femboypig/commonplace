#!/usr/bin/env python3
"""Build Apple's bootstrap namespace RPC clients from launchd."""

import re

from darwin_build import OUT, compile_source, archive, prepare_source
from mach_interface import generate_interface


def main():
    source = prepare_source("launchd")
    generated = OUT / "launch"
    interface = generate_interface("job", source / "src/job.defs", generated)
    manager = prepare_source("launchd_manager", "launchd") / "src"
    definition = generated / "bootstrap_legacy.defs"
    contents = (
        (manager / "protocol_vproc.defs")
        .read_text()
        .replace("userprefix vproc_mig_;", "userprefix commonplace_vproc_mig_;")
    )
    contents = re.sub(
        r"(\b(?:simple)?routine\s+)([A-Za-z_]\w*)", r"\1legacy_\2", contents
    )
    if not definition.exists() or definition.read_text() != contents:
        definition.write_text(contents)
    legacy = generate_interface(
        "bootstrap_legacy", definition, generated, includes=(manager,)
    )
    flags = [
        "-fblocks",
        "-DMIG_SERVER_ROUTINE=",
        "-DOSATOMIC_USE_INLINED=1",
        "-I" + str(source / "src"),
        "-I" + str(source / "liblaunch"),
        "-I" + str(generated),
        "-Wno-deprecated-declarations",
    ]
    objects = [
        compile_source(
            source / "liblaunch/libbootstrap.c", OUT / "obj/launch/bootstrap.o", flags
        ),
        compile_source(interface["user"], OUT / "obj/launch/jobUser.o", flags),
    ]
    objects.append(
        compile_source(legacy["user"], OUT / "obj/launch/bootstrap_legacy.o", flags)
    )
    archive(OUT / "lib/libsystem_bootstrap.a", objects)


if __name__ == "__main__":
    main()
