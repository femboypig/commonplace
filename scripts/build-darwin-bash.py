#!/usr/bin/env python3
"""Cross-build Apple's bash with the native static Darwin libraries."""

import os
import json
import hashlib
import shlex
import shutil
import subprocess
from darwin_build import ROOT, OUT, CC, CFLAGS, SDK, RESOURCE, prepare_source


def main():
    project = prepare_source("bash")
    source = project / "bash-3.2"
    directory = OUT / "bash"
    directory.mkdir(parents=True, exist_ok=True)
    flags = [flag for flag in CFLAGS if flag not in ("-std=gnu11", "-g")]
    flags += [
        "-std=gnu89",
        "-Wno-deprecated-non-prototype",
        "-Wno-deprecated-declarations",
        "-Wno-error=incompatible-pointer-types",
        "-fno-strict-aliasing",
    ]
    libraries = [
        OUT / "obj/runtime/start-asm.o",
        OUT / "lib/libsystem_info_file.a",
        OUT / "lib/libsystem_c_bootstrap.a",
        OUT / "lib/libsystem_kernel.a",
    ]
    environment = {
        **os.environ,
        "CC": str(CC),
        "CC_FOR_BUILD": "cc",
        "CFLAGS": shlex.join(flags),
        "CONFIG_SITE": "/dev/null",
        "CFLAGS_FOR_BUILD": "-O2 -std=gnu89",
        "bash_cv_job_control_missing": "present",
        "bash_cv_sys_named_pipes": "present",
        "CPPFLAGS": shlex.join(
            [
                "-static",
                "-fno-blocks",
                "-D_FORTIFY_SOURCE=0",
                "-nostdlibinc",
                "-isystem",
                str(SDK / "usr/include"),
                "-isystem",
                str(RESOURCE / "include"),
            ]
        ),
        "LDFLAGS": shlex.join(
            [
                "--ld-path=" + str(ROOT / "toolchain/bin/x86_64-apple-darwin15-ld"),
                "-mno-outline",
                "-static",
                "-nostdlib",
                "-Wl,-Z,-fatal_warnings,-e,_start,-dead_strip",
            ]
        ),
        "LIBS": shlex.join(map(str, libraries)),
        "AR": str(ROOT / "toolchain/bin/x86_64-apple-darwin15-ar"),
        "RANLIB": str(ROOT / "toolchain/bin/x86_64-apple-darwin15-ranlib"),
    }
    target = json.loads((ROOT / "sources.lock.json").read_text())["target"]
    release = target.rsplit("darwin", 1)[1]
    ostype = '#define OSTYPE "darwin' + release + '"\n'
    if (
        not (directory / "ostype.h").exists()
        or (directory / "ostype.h").read_text() != ostype
    ):
        (directory / "ostype.h").write_text(ostype)
    signature = hashlib.sha256(
        json.dumps(
            {
                key: environment[key]
                for key in (
                    "CC",
                    "CC_FOR_BUILD",
                    "CFLAGS",
                    "CFLAGS_FOR_BUILD",
                    "CPPFLAGS",
                    "LDFLAGS",
                    "LIBS",
                    "AR",
                    "RANLIB",
                    "bash_cv_job_control_missing",
                    "bash_cv_sys_named_pipes",
                )
            },
            sort_keys=True,
        ).encode()
    )
    for library in libraries:
        signature.update(library.read_bytes())
    signature.update((project / ".commonplace-patches.sha256").read_bytes())
    headers = hashlib.sha256()
    for header in sorted((SDK / "usr/include").rglob("*.h")):
        headers.update(str(header.relative_to(SDK)).encode())
        headers.update(header.read_bytes())
    signature.update(headers.digest())
    header_stamp = directory / "sdk.sha256"
    if (directory / "Makefile").exists() and (
        not header_stamp.exists() or header_stamp.read_text() != headers.hexdigest()
    ):
        subprocess.run(["make", "clean"], cwd=directory, env=environment, check=True)
    header_stamp.write_text(headers.hexdigest())
    stamp = directory / "configure.sha256"
    if not stamp.exists() or stamp.read_text() != signature.hexdigest():
        shutil.rmtree(directory / "conftest.dSYM", ignore_errors=True)
        subprocess.run(
            [
                "bash",
                str(source / "configure"),
                "--host=x86_64-apple-darwin15",
                "--build=x86_64-pc-linux-gnu",
                "--without-bash-malloc",
                "--disable-readline",
                "--disable-nls",
                "--disable-progcomp",
                "--disable-net-redirections",
                "--prefix=/usr",
            ],
            cwd=directory,
            env=environment,
            check=True,
        )
        stamp.write_text(signature.hexdigest())
    (directory / "native-libraries.mk").write_text(
        "bash: " + " ".join(map(str, libraries)) + "\n"
    )
    subprocess.run(
        [
            "make",
            "-f",
            "Makefile",
            "-f",
            "native-libraries.mk",
            "-j2",
            "LDFLAGS_FOR_BUILD=",
            "LIBS_FOR_BUILD=",
            "bash",
        ],
        cwd=directory,
        env=environment,
        check=True,
    )
    (OUT / "bin").mkdir(exist_ok=True)
    shutil.copyfile(directory / "bash", OUT / "bin/bash")
    print("native Apple bash: " + str(OUT / "bin/bash"))


if __name__ == "__main__":
    main()
