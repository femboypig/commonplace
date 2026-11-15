"""Exclusive, recoverable transactions on offline HFS+ system images."""

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import shutil
import stat
import struct
import tempfile
from create_disk_image import validate_image, sync_directory


@contextmanager
def locked_image(path, *, allow_unclean=False):
    with path.open("r+b") as stream:
        try:
            fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("disk is in use; shut down its VM first: " + str(path))
        identity = os.fstat(stream.fileno())
        validate_image(path)
        stream.seek(1028)
        attributes = struct.unpack(">I", stream.read(4))[0]
        if not allow_unclean and not attributes & 0x100:
            raise ValueError("disk was not cleanly unmounted; use recovery first")
        yield identity


@dataclass(frozen=True)
class ImageTransaction:
    staged: Path
    source: Path
    backup: Path


@contextmanager
def image_transaction(path, stamp, *, restore=None, allow_unclean=False):
    path = Path(path).resolve(strict=True)
    source = Path(restore).resolve(strict=True) if restore else path
    if restore and source.samefile(path):
        raise ValueError("rollback source must be a different image")
    # Retain a stable lock across replacement of the disk inode. All maintenance
    # operations share this lock as well as QEMU's byte-range locks on the image.
    lock_fd = os.open(
        path.with_name(path.name + ".update.lock"),
        os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(lock_fd, "rb+") as lock:
        identity = os.fstat(lock.fileno())
        if not stat.S_ISREG(identity.st_mode) or identity.st_nlink != 1:
            raise ValueError("maintenance lock must be a regular file with one link")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("another maintenance operation is using this disk")
        with locked_image(
            path, allow_unclean=allow_unclean or bool(restore)
        ) as identity:
            with tempfile.TemporaryDirectory(
                dir=path.parent, prefix=".update-"
            ) as temporary:
                staged = Path(temporary) / "system.hfs"
                if restore:
                    with locked_image(source):
                        shutil.copyfile(source, staged)
                else:
                    shutil.copyfile(source, staged)
                backup = path.with_name(path.name + ".previous-" + stamp)
                yield ImageTransaction(staged, source, backup)
                current = path.stat()
                if (current.st_dev, current.st_ino) != (
                    identity.st_dev,
                    identity.st_ino,
                ):
                    raise ValueError("system image changed during maintenance")
                shutil.copystat(path, staged)
                with staged.open("rb") as stream:
                    os.fsync(stream.fileno())
                os.link(path, backup)
                sync_directory(path.parent)
                os.replace(staged, path)
                sync_directory(path.parent)


@contextmanager
def maintenance_signals():
    """Let VM and staging cleanup run when a maintenance command is terminated."""
    import signal

    def interrupted(number, frame):
        raise SystemExit(128 + number)

    previous = {
        number: signal.signal(number, interrupted)
        for number in (signal.SIGTERM, signal.SIGHUP)
    }
    try:
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
