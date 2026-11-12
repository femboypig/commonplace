#!/usr/bin/env python3
"""Create the persistent HFS+ data disk once; preserve every existing image."""

import argparse
from pathlib import Path
import subprocess
import tempfile
from create_disk_image import validate_image as validate, publish_image

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "build/disks/data.hfs"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT)
    parser.add_argument(
        "--size", type=int, default=64, help="size of a new image in MiB"
    )
    options = parser.parse_args()
    path = options.path.resolve()
    if path.exists():
        validate(path)
        print("preserving persistent disk: " + str(path))
        return
    if not 16 <= options.size <= 1024:
        parser.error("size must be 16..1024 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent, prefix=".create-") as temporary:
        image = Path(temporary) / "data.hfs"
        with image.open("wb") as output:
            output.truncate(options.size * 1024 * 1024)
        subprocess.run(
            [
                str(ROOT / "toolchain/bin/newfs_hfs"),
                "-J",
                "-v",
                "commonplace-data",
                "-U",
                "0",
                "-G",
                "0",
                "-M",
                "755",
                str(image),
            ],
            check=True,
        )
        validate(image)
        publish_image(image, path)
    print("persistent disk ready: " + str(path))


if __name__ == "__main__":
    main()
