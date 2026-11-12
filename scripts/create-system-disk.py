#!/usr/bin/env python3
"""Install a journaled HFS+ system disk once, preserving existing installations."""

import argparse
from pathlib import Path
import tempfile
from create_disk_image import validate_image, publish_image
from rootfs_image import ROOT, build_image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=ROOT / "build/disks/system.hfs")
    parser.add_argument("--size", type=int, default=256, help="new disk size in MiB")
    options = parser.parse_args()
    path = options.path.resolve()
    if path.exists():
        validate_image(path)
        print("preserving installed system: " + str(path))
        return
    if not 32 <= options.size <= 1024:
        parser.error("size must be 32..1024 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent, prefix=".install-") as temporary:
        image = Path(temporary) / "system.hfs"
        build_image(image, options.size, persistent=True)
        validate_image(image)
        publish_image(image, path)
    print("persistent system ready: " + str(path))


if __name__ == "__main__":
    main()
