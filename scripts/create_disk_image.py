"""Validation and atomic installation of persistent HFS+ images."""

import os


def validate_image(path):
    if (
        not path.is_file()
        or path.stat().st_size < 16 * 1024 * 1024
        or path.stat().st_size % 512
    ):
        raise ValueError("not a supported disk image: " + str(path))
    with path.open("rb") as stream:
        stream.seek(1024)
        if stream.read(2) not in (b"H+", b"HX"):
            raise ValueError("existing image is not HFS+: " + str(path))


def publish_image(image, path):
    with image.open("rb") as stream:
        os.fsync(stream.fileno())
    try:
        os.link(image, path)
    except FileExistsError:
        validate_image(path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
