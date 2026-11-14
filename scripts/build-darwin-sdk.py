#!/usr/bin/env python3
"""Assemble Darwin userspace headers from the pinned public source projects."""

from pathlib import Path
import shutil
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SDK = ROOT / "build/darwin-sdk"


def headers(source, destination, excluded=()):
    for path in sorted(source.rglob("*.h")):
        relative = path.relative_to(source)
        if str(relative) in excluded:
            continue
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, output)


def prepare(sdk):
    include = sdk / "usr/include"
    include.mkdir(parents=True, exist_ok=True)
    exports = ROOT / "build/xnu/obj/EXPORT_HDRS"
    for component in ("osfmk", "bsd", "libkern", "iokit"):
        source = exports / component
        if not source.is_dir():
            raise SystemExit("run make xnu-headers before assembling the Darwin SDK")
        headers(source, include)
    headers(ROOT / "sources/xnu/EXTERNAL_HEADERS", include)
    (include / "System/i386").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        ROOT / "sources/xnu/osfmk/i386/cpu_capabilities.h",
        include / "System/i386/cpu_capabilities.h",
    )
    for name in (
        "aio.h",
        "times.h",
        "utsname.h",
        "timeb.h",
        "process_policy.h",
        "dtrace.h",
        "dtrace_glue.h",
        "csr.h",
        "codesign.h",
    ):
        shutil.copyfile(ROOT / "sources/xnu/bsd/sys" / name, include / "sys" / name)
    (include / "System/machine").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        ROOT / "sources/xnu/osfmk/machine/cpu_capabilities.h",
        include / "System/machine/cpu_capabilities.h",
    )
    headers(ROOT / "sources/xnu/libsyscall/mach/mach", include / "mach")
    headers(ROOT / "sources/xnu/libsyscall/wrappers", include)
    headers(ROOT / "sources/xnu/libsyscall/wrappers/spawn", include)
    for directory, name in (
        ("System/sys", "content_protection.h"),
        ("Kernel/sys", "decmpfs.h"),
    ):
        (include / directory).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "sources/xnu/bsd/sys" / name, include / directory / name)
    headers(ROOT / "sources/cctools/cctools/include/mach-o", include / "mach-o")
    headers(ROOT / "sources/dyld/include", include)
    for name in ("pwd.h", "grp.h", "netdb.h", "aliasdb.h"):
        shutil.copyfile(ROOT / "sources/libinfo/lookup.subproj" / name, include / name)
    headers(ROOT / "sources/libinfo/membership.subproj", include)
    shutil.copyfile(
        ROOT / "sources/libinfo/gen.subproj/ifaddrs.h", include / "ifaddrs.h"
    )
    for name in ("copyfile.h", "xattr_flags.h"):
        shutil.copyfile(ROOT / "sources/copyfile" / name, include / name)
    shutil.copyfile(ROOT / "sources/removefile/removefile.h", include / "removefile.h")
    shutil.copyfile(ROOT / "sources/libutil/libutil.h", include / "libutil.h")
    shutil.copyfile(ROOT / "sources/libc/gen/get_compat.h", include / "get_compat.h")
    headers(ROOT / "sources/libc/include", include, ("sys/cdefs.h",))
    shutil.copyfile(ROOT / "sources/libresolv/nameser.h", include / "arpa/nameser.h")
    headers(ROOT / "sources/libc/include/FreeBSD", include)
    headers(ROOT / "sources/libc/include/NetBSD", include)
    headers(ROOT / "sources/architecture", include / "architecture")
    headers(ROOT / "sources/libpthread/sys", include / "sys")
    headers(ROOT / "sources/libpthread/pthread", include / "pthread")
    headers(ROOT / "sources/libpthread/private", include / "pthread", ("qos.h",))
    for name in ("pthread.h", "pthread_impl.h", "sched.h"):
        shutil.copyfile(include / "pthread" / name, include / name)
    for name in ("Block.h", "Block_private.h"):
        shutil.copyfile(ROOT / "sources/libclosure" / name, include / name)
    headers(ROOT / "sources/libmalloc/include", include)
    headers(ROOT / "sources/libplatform/include", include)
    shutil.copyfile(
        ROOT / "sources/libsystem/alloc_once_private.h",
        include / "os/alloc_once_private.h",
    )
    headers(ROOT / "sources/libm/Source/Intel", include)
    shutil.copyfile(
        ROOT / "sources/libpthread/private/spinlock_private.h",
        include / "pthread_spinlock.h",
    )
    headers(ROOT / "userland/darwin/include", include)
    generator = sdk / "usr/local/libexec/availability.pl"
    generator.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "sources/availabilityversions/availability.pl", generator)
    generator.chmod(0o755)
    subprocess.run(
        [
            "bash",
            str(ROOT / "sources/xnu/bsd/sys/make_symbol_aliasing.sh"),
            str(sdk),
            str(include / "sys/_symbol_aliasing.h"),
        ],
        check=True,
    )
    subprocess.run(
        [
            "bash",
            str(ROOT / "sources/xnu/bsd/sys/make_posix_availability.sh"),
            str(include / "sys/_posix_availability.h"),
        ],
        check=True,
    )
    for header in include.rglob("*.h"):
        contents = header.read_bytes()
        stripped = re.sub(
            rb"^//Begin-Libc.*?^//End-Libc[^\n]*\n?", b"", contents, flags=re.M | re.S
        )
        if stripped != contents:
            header.write_bytes(stripped)


def main():
    SDK.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=SDK.parent, prefix=".darwin-sdk-"
    ) as temporary:
        staging = Path(temporary)
        prepare(staging)
        expected = set()
        for source in sorted(staging.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(staging)
            expected.add(relative)
            destination = SDK / relative
            if (
                not destination.is_file()
                or destination.read_bytes() != source.read_bytes()
            ):
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                destination.chmod(source.stat().st_mode & 0o777)
        for path in SDK.rglob("*"):
            if path.is_file() and path.relative_to(SDK) not in expected:
                path.unlink()
    print("Darwin userspace SDK: " + str(SDK))


if __name__ == "__main__":
    main()
