#!/usr/bin/env python3
"""Build Apple's notification client and in-process notification engine."""

from darwin_build import OUT, compile_source, archive, prepare_source
from mach_interface import generate_interface

from darwin_diagnostics import diagnostic_flags


def main():
    source = prepare_source("libnotify")
    generated = OUT / "notify"
    interface = generate_interface("notify_ipc", source / "notify_ipc.defs", generated)
    flags = [
        "-fblocks",
        *diagnostic_flags(),
        "-DMIG_SERVER_ROUTINE=",
        "-DOSATOMIC_USE_INLINED=1",
        "-I" + str(source),
        "-I" + str(generated),
        "-Wno-deprecated-declarations",
    ]
    objects = [
        compile_source(source / name, OUT / "obj/notify" / (name + ".o"), flags)
        for name in ("libnotify.c", "notify_client.c", "table.c")
    ]
    objects.append(
        compile_source(interface["user"], OUT / "obj/notify/notify_ipcUser.o", flags)
    )
    archive(OUT / "lib/libsystem_notify.a", objects)


if __name__ == "__main__":
    main()
