#!/usr/bin/env python3
"""Build XNU's native syscall stubs for static, non-cancelable bootstrap programs."""

from concurrent.futures import ThreadPoolExecutor
import os
import hashlib
import subprocess
from pathlib import Path
from darwin_build import ROOT, OUT, compile_source, archive, prepare_source


def main():
    source = prepare_source("xnu", "libsyscall", "libsyscall").parent
    generated = OUT / "syscalls"
    generated.mkdir(parents=True, exist_ok=True)
    signature = hashlib.sha256(b"x86_64:MacOSX")
    inputs = [
        ROOT / "sources/xnu/bsd/kern/syscalls.master",
        source / "libsyscall/xcodescripts/create-syscalls.pl",
    ]
    for directory in ("custom", "Platforms"):
        inputs.extend(
            path
            for path in (source / "libsyscall" / directory).rglob("*")
            if path.is_file()
        )
    for path in sorted(inputs):
        signature.update(str(path).encode())
        signature.update(path.read_bytes())
    stamp = generated / ".inputs.sha256"
    if not stamp.exists() or stamp.read_text() != signature.hexdigest():
        subprocess.run(
            [
                "perl",
                str(source / "libsyscall/xcodescripts/create-syscalls.pl"),
                str(ROOT / "sources/xnu/bsd/kern/syscalls.master"),
                str(source / "libsyscall/custom"),
                str(source / "libsyscall/Platforms"),
                "MacOSX",
                str(generated),
            ],
            env={**os.environ, "ARCHS": "x86_64"},
            check=True,
            stdout=subprocess.DEVNULL,
        )
        stamp.write_text(signature.hexdigest())

    def assemble(path):
        return compile_source(
            path,
            OUT / "obj/libsyscall" / path.with_suffix(".o").name,
            [
                "-x",
                "assembler-with-cpp",
                "-DPRIVATE",
                "-D__DYNAMIC__=1",
                "-Dcerror=cerror_nocancel",
                "-D_cerror=_cerror_nocancel",
            ],
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        objects = list(pool.map(assemble, sorted(generated.glob("*.s"))))
    objects.append(
        compile_source(
            source / "libsyscall/custom/errno.c",
            OUT / "obj/libsyscall/errno.o",
            ["-I" + str(source / "libsyscall/os")],
        )
    )
    for name in (
        "kill.c",
        "ioctl.c",
        "unix03/getrlimit.c",
        "unix03/setrlimit.c",
        "unix03/chmod.c",
        "unix03/fchmod.c",
        "unix03/mmap.c",
        "unix03/munmap.c",
        "cancelable/fcntl-cancel.c",
        "cancelable/sigsuspend-cancel.c",
        "setpriority.c",
        "rmdir.c",
        "unlink.c",
        "open_dprotected_np.c",
        "remove-counter.c",
        "rename.c",
        "renameat.c",
        "unlinkat.c",
        "spawn/posix_spawn.c",
    ):
        objects.append(
            compile_source(
                source / "libsyscall/wrappers" / name,
                OUT
                / "obj/libsyscall/wrappers"
                / name.replace("/", "-").replace(".c", ".o"),
                [
                    "-DPRIVATE",
                    "-D__APPLE_API_PRIVATE",
                    "-iquote" + str(source / "libsyscall/mach"),
                ],
            )
        )
    objects.append(
        compile_source(
            source / "libsyscall/mach/mach_init.c",
            OUT / "obj/libsyscall/mach_init.o",
            ["-DPRIVATE"],
        )
    )
    for name in (
        "mach/mach_traps.s",
        "wrappers/mach_absolute_time.s",
        "wrappers/__commpage_gettimeofday.s",
    ):
        objects.append(
            compile_source(
                source / "libsyscall" / name,
                OUT / "obj/libsyscall" / Path(name).with_suffix(".o"),
                ["-x", "assembler-with-cpp", "-DPRIVATE", "-D__DYNAMIC__=1"],
            )
        )
    for name in ("mach_error_string.c", "error_codes.c", "mach_error.c"):
        objects.append(
            compile_source(
                source / "libsyscall/mach" / name,
                OUT / "obj/libsyscall" / Path(name).with_suffix(".o"),
                ["-DVARIANT_STATIC=1"],
            )
        )
    archive(OUT / "lib/libsystem_kernel.a", objects)
    print("native Darwin syscall library: " + str(OUT / "lib/libsystem_kernel.a"))


if __name__ == "__main__":
    main()
