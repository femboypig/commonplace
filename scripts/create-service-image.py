#!/usr/bin/env python3
"""Install the native Apple service image without replacing existing disks."""

import argparse
from pathlib import Path
import tempfile
from create_disk_image import validate_image, publish_image
from rootfs_image import ROOT
from service_image import build_service_image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=ROOT / "build/disks/services.hfs")
    parser.add_argument("--size", type=int, default=256, help="new disk size in MiB")
    options = parser.parse_args()
    path = options.path.resolve()
    if path.exists():
        validate_image(path)
        print("preserving installed service system: " + str(path))
        return
    if not 64 <= options.size <= 1024:
        parser.error("size must be 64..1024 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent, prefix=".services-") as directory:
        image = Path(directory) / "system.hfs"
        build_service_image(image, options.size)
        validate_image(image)
        publish_image(image, path)
    print("native Apple service system ready: " + str(path))


if __name__ == "__main__":
    main()
