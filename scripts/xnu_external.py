"""Stage pinned Apple kernel families and their public include layout."""

from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ("iopci", "ionetwork", "rtl8139")


def install_sources(staged, destination):
    """Preserve unchanged mtimes, including when a source patch is removed."""
    expected = {path.relative_to(staged) for path in staged.rglob("*")}
    destination.mkdir(exist_ok=True)
    for relative in sorted(expected):
        source = staged / relative
        output = destination / relative
        if source.is_symlink():
            target = source.readlink()
            if not output.is_symlink() or output.readlink() != target:
                if output.exists() or output.is_symlink():
                    output.unlink()
                output.symlink_to(target)
        elif source.is_dir():
            output.mkdir(exist_ok=True)
        elif not output.is_file() or output.read_bytes() != source.read_bytes():
            shutil.copyfile(source, output)
            shutil.copymode(source, output)
    for path in sorted(destination.rglob("*"), reverse=True):
        if path.relative_to(destination) not in expected:
            if path.is_dir() and not path.is_symlink():
                path.rmdir()
            else:
                path.unlink()


def prepare_external(source, apply_patches):
    external = source / "external"
    external.mkdir(exist_ok=True)
    for project in PROJECTS:
        with tempfile.TemporaryDirectory(dir=external, prefix=".stage-") as temporary:
            staged = Path(temporary) / project
            shutil.copytree(ROOT / "sources" / project, staged, symlinks=True)
            apply_patches(staged, project)
            install_sources(staged, external / project)
    headers = external / "IOKit"
    headers.mkdir(exist_ok=True)
    for name, target in (("pci", "../iopci/IOKit/pci"),
                         ("network", "../ionetwork")):
        link = headers / name
        if not link.exists():
            link.symlink_to(target, target_is_directory=True)
