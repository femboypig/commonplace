"""Assemble a bootable native Apple service-manager image."""

import subprocess
import tempfile
from pathlib import Path
from rootfs_image import ROOT, build_image, system_directories
from service_payload import DIRECTORIES, service_files, service_defaults, service_mode


def build_service_image(image, size_mib=96, persistent=True, *, console_login=True):
    image = Path(image)
    build_image(image, size_mib, persistent=persistent)
    hfs = ROOT / "toolchain/bin/hfsplus"

    def run(*arguments):
        subprocess.run([str(hfs), str(image), *map(str, arguments)], check=True)

    base_directories = system_directories()
    for path in DIRECTORIES:
        # hfsplus mkdir recreates existing catalog records. Base image paths
        # already exist and must retain their original directory identities.
        if path not in base_directories:
            run("mkdir", path)
    run("chmod", "1777", "/var/tmp")
    with tempfile.TemporaryDirectory(
        dir=image.parent, prefix=".services-"
    ) as directory:
        temporary = Path(directory)
        files = {
            **service_files(),
            **service_defaults(temporary, console_login=console_login),
        }
        for target, source in files.items():
            run("add", source, target)
            run("chmod", service_mode(target), target)
        if console_login:
            marker = temporary / "setup-required"
            marker.write_text("root password setup\n")
            run("add", marker, "/etc/commonplace.setup-required")
            run("chmod", "600", "/etc/commonplace.setup-required")
