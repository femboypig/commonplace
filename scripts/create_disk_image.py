"""Validation and atomic installation of persistent HFS+ images."""

import os


def validate_open_image(stream, path):
    """Validate an already open image without releasing its POSIX record locks."""
    import stat

    status = os.fstat(stream.fileno())
    if (
        not stat.S_ISREG(status.st_mode)
        or status.st_size < 16 * 1024 * 1024
        or status.st_size % 512
    ):
        raise ValueError("not a supported disk image: " + str(path))
    stream.seek(1024)
    if stream.read(2) not in (b"H+", b"HX"):
        raise ValueError("existing image is not HFS+: " + str(path))


def validate_image(path):
    if not path.is_file():
        raise ValueError("not a supported disk image: " + str(path))
    with path.open("rb") as stream:
        validate_open_image(stream, path)


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_image(image, path):
    with image.open("rb") as stream:
        os.fsync(stream.fileno())
    try:
        os.link(image, path)
    except FileExistsError:
        validate_image(path)
    sync_directory(path.parent)
