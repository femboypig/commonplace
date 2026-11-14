#!/usr/bin/env python3
"""Exercise Apple's local identity, PAM and BSD logging APIs inside QEMU."""

from datetime import datetime, timezone
import json
import shutil
import subprocess
import sys
from darwin_build import ROOT, OUT, LD, compile_source


def main():
    directory = (
        ROOT
        / "build/admin-checks"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    directory.mkdir(parents=True)
    image = directory / "recovery.hfs"
    shutil.copyfile(ROOT / "build/rootfs/root.hfs", image)
    objects = [
        compile_source(
            ROOT / "tests/guest" / (name + ".c"), OUT / "obj/tests" / (name + ".o")
        )
        for name in ("admin_runtime", "syslog_lifecycle")
    ]
    probe = directory / "admin-check"
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
            "-no_uuid",
            "-o",
            str(probe),
            *map(str, objects),
            str(OUT / "system/libpam.2.dylib"),
            str(OUT / "system/libSystem.B.dylib"),
        ],
        check=True,
    )
    policy = directory / "policy"
    policy.write_text(
        "auth required pam_rootok.so\naccount required pam_self.so\npassword required pam_deny.so\nsession required pam_deny.so\n"
    )
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    for path, file in (
        ("/bin/admin-check", probe),
        ("/etc/pam.d/commonplace-test", policy),
    ):
        subprocess.run([hfs, str(image), "add", str(file), path], check=True)
    subprocess.run([hfs, str(image), "chmod", "755", "/bin/admin-check"], check=True)
    cases = directory / "cases.json"
    cases.write_text(
        json.dumps(
            [
                {
                    "name": "native admin runtime",
                    "send": "admin-check; echo admin-status:$?\n",
                    "expect": r"native admin: reentrant accounts, syslog, PAM policy and privilege checks passed[\s\S]*admin-status:0",
                }
            ]
        )
        + "\n"
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/boot-qemu.py"),
            "--root-image",
            str(image),
            "--seconds",
            "180",
            "--check-console",
            "--console-case-file",
            str(cases),
            "--expect-shutdown",
            "poweroff",
            "--output",
            str(directory / "boot"),
        ],
        check=True,
    )
    print("native administration runtime passed: " + str(directory))


if __name__ == "__main__":
    main()
