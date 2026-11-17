#!/usr/bin/env python3
"""Build the RAM recovery root without mounting an image on the host."""

import hashlib
import json
import tempfile
import subprocess
from pathlib import Path
from rootfs_image import ROOT, build_image, system_symlinks


def main():
    directory = ROOT / "build/rootfs"
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory, prefix=".image-") as temporary:
        image = Path(temporary) / "root.hfs"
        hashes = build_image(image)
        hfs = str(ROOT / "toolchain/bin/hfsplus")
        helper = ROOT / "userland/darwin/recovery/password.sh"
        target = "/usr/libexec/commonplace/recover-password"
        subprocess.run([hfs, str(image), "add", str(helper), target], check=True)
        subprocess.run([hfs, str(image), "chmod", "755", target], check=True)
        extracted = Path(temporary) / "verify-password-helper"
        subprocess.run([hfs, str(image), "extract", target, str(extracted)], check=True)
        if extracted.read_bytes() != helper.read_bytes():
            raise ValueError("recovery helper round-trip verification failed")
        hashes[target] = hashlib.sha256(helper.read_bytes()).hexdigest()
        image.replace(directory / "root.hfs")
    image = directory / "root.hfs"
    metadata = {
        "image": "build/rootfs/root.hfs",
        "size": image.stat().st_size,
        "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "init_sha256": hashlib.sha256(
            (ROOT / "build/userland/init").read_bytes()
        ).hexdigest(),
        "programs": hashes,
        "symlinks": system_symlinks(),
    }
    (directory / "image.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
