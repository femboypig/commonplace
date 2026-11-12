#!/usr/bin/env python3
"""Build the RAM recovery root without mounting an image on the host."""

import hashlib
import json
import tempfile
from pathlib import Path
from rootfs_image import ROOT, build_image


def main():
    directory = ROOT / "build/rootfs"
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory, prefix=".image-") as temporary:
        image = Path(temporary) / "root.hfs"
        hashes = build_image(image)
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
    }
    (directory / "image.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
