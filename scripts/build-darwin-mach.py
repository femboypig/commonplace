#!/usr/bin/env python3
"""Build the native Mach RPC clients and syscall wrappers from XNU."""

import subprocess
import hashlib
from darwin_build import ROOT, OUT, SDK, compile_source, archive, prepare_source


def main():
    source = prepare_source("xnu", "libsyscall", "libsyscall")
    generated = OUT / "mach"
    generated.mkdir(parents=True, exist_ok=True)
    interfaces = (
        "mach_vm",
        "vm_map",
        "mach_port",
        "thread_act",
        "task",
        "mach_host",
        "host_priv",
        "clock",
        "clock_priv",
        "mach_voucher",
    )
    internal = {"mach_vm", "vm_map", "mach_port", "thread_act"}
    signature = hashlib.sha256()
    for directory in (
        ROOT / "sources/xnu/osfmk/mach",
        ROOT / "sources/xnu/bsd",
        SDK / "usr/include",
    ):
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix in (".h", ".defs"):
                signature.update(str(path).encode())
                signature.update(path.read_bytes())
    signature.update((ROOT / "toolchain/bin/mig").read_bytes())
    fingerprint = signature.hexdigest()
    stamp = generated / ".inputs.sha256"
    regenerate = not stamp.exists() or stamp.read_text() != fingerprint
    objects = []
    for name in interfaces:
        definition = ROOT / "sources/xnu/osfmk/mach" / f"{name}.defs"
        header = generated / (name + "_internal.h" if name in internal else name + ".h")
        user = generated / f"{name}User.c"
        if regenerate or not header.exists() or not user.exists():
            subprocess.run(
                [
                    str(ROOT / "toolchain/bin/mig"),
                    "-novouchers",
                    "-arch",
                    "i386",
                    "-I" + str(ROOT / "sources/xnu/osfmk"),
                    "-I" + str(ROOT / "sources/xnu/bsd"),
                    "-I" + str(SDK / "usr/include"),
                    "-DPRIVATE",
                    "-header",
                    str(header),
                    "-user",
                    str(user),
                    "-server",
                    "/dev/null",
                    str(definition),
                ],
                check=True,
            )
        objects.append(
            compile_source(
                user,
                OUT / "obj/mach" / f"{name}User.o",
                ["-I" + str(generated), "-DPRIVATE", "-DMIG_SERVER_ROUTINE="],
            )
        )
    stamp.write_text(fingerprint)
    for name in (
        "mach_vm.c",
        "mach_port.c",
        "thread_act.c",
        "mach_msg.c",
        "semaphore.c",
        "mach_legacy.c",
        "ms_thread_switch.c",
        "mig_reply_port.c",
        "mig_strncpy.c",
        "mig_allocate.c",
        "mig_deallocate.c",
    ):
        path = source / "mach" / name
        if not path.exists():
            raise ValueError("missing Mach wrapper: " + str(path))
        objects.append(
            compile_source(
                path,
                OUT / "obj/mach" / path.with_suffix(".o").name,
                [
                    "-Wno-int-conversion",
                    "-DPRIVATE",
                    "-I" + str(generated.parent),
                    "-iquote" + str(source / "mach"),
                    "-I" + str(source / "os"),
                    "-I" + str(source / "wrappers"),
                    "-I" + str(source / "wrappers/libproc"),
                ],
            )
        )
    objects.append(
        compile_source(source / "os/alloc_once.c", OUT / "obj/mach/alloc_once.o")
    )
    for name in (
        "_libkernel_init.c",
        "init_cpu_capabilities.c",
        "csr.c",
        "cancelable/select.c",
        "cancelable/select-cancel.c",
        "libproc/libproc.c",
    ):
        objects.append(
            compile_source(
                source / "wrappers" / name,
                OUT / "obj/mach" / name.replace("/", "-").replace(".c", ".o"),
                [
                    "-DPRIVATE",
                    "-fPIC",
                    "-Wno-int-conversion",
                    "-I" + str(source / "os"),
                    "-I" + str(source / "wrappers"),
                    "-I" + str(source / "wrappers/libproc"),
                ],
            )
        )
    objects.append(
        compile_source(
            source / "wrappers/__get_cpu_capabilities.s",
            OUT / "obj/mach/cpu.o",
            ["-x", "assembler-with-cpp", "-DPRIVATE"],
        )
    )
    objects.append(
        compile_source(
            source / "wrappers/_libc_funcptr.c",
            OUT / "obj/mach/upcalls.o",
            [
                "-DPRIVATE",
                "-fPIC",
                "-Dmalloc=__kernel_malloc",
                "-Dfree=__kernel_free",
                "-Drealloc=__kernel_realloc",
                "-Dreallocf=__kernel_reallocf",
                "-D_pthread_set_self=__kernel_pthread_set_self",
                "-D_pthread_exit_if_canceled=__kernel_pthread_exit_if_canceled",
                "-D_pthread_clear_qos_tsd=__kernel_pthread_clear_qos_tsd",
            ],
        )
    )
    archive(OUT / "lib/libsystem_mach.a", objects)


if __name__ == "__main__":
    main()
