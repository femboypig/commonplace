"""Construct the native recovery transaction for each installed system profile."""

from pathlib import Path, PurePosixPath
import subprocess
import shlex
from rootfs_image import ROOT, system_files, system_symlinks
from service_payload import (
    PROFILE,
    DIRECTORIES,
    service_files,
    service_defaults,
    service_mode,
)

PAYLOAD = "/tmp/update-payload"
IDENTITY_FILES = {"/etc/passwd", "/etc/master.passwd", "/etc/group"}
VERSION = "/System/Library/CoreServices/SystemVersion.plist"


def prepare_payload(directory, recovery):
    defaults = service_defaults(directory)
    managed = service_files()
    managed[VERSION] = defaults.pop(VERSION)
    files = {**managed, **defaults}
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    parents = {PAYLOAD}
    for target in files:
        parents.update(
            PAYLOAD + str(parent)
            for parent in PurePosixPath(target).parents
            if str(parent) != "/"
        )
    for parent in sorted(
        parents, key=lambda value: (len(PurePosixPath(value).parts), value)
    ):
        subprocess.run([hfs, str(recovery), "mkdir", parent], check=True)
    for target, source in files.items():
        if not source.is_file():
            raise ValueError("build darwin-services before updating: " + str(source))
        destination = PAYLOAD + target
        subprocess.run(
            [hfs, str(recovery), "add", str(source), destination], check=True
        )
        subprocess.run(
            [hfs, str(recovery), "chmod", service_mode(target), destination], check=True
        )
        extracted = Path(directory) / "verify-payload"
        subprocess.run(
            [hfs, str(recovery), "extract", destination, str(extracted)], check=True
        )
        if extracted.read_bytes() != source.read_bytes():
            raise ValueError("recovery payload verification failed: " + target)
    return {target: PAYLOAD + target for target in managed}, {
        target: PAYLOAD + target for target in defaults
    }


def update_commands(managed, defaults):
    commands = [
        "root=/tmp/system",
        'mkdir "$root"',
        'mount -t hfs /dev/cp1 "$root"',
        "umask 077",
        'mkdir "$root/.commonplace-update"',
        """ensure_directory() {
    directory=$root$1
    test ! -L "$directory"
    test ! -e "$directory" || test -d "$directory"
    mkdir -p -m 755 "$directory"
}""",
        """install_file() {
    source=$1
    target=$root$2
    test ! -L "$target"
    test ! -e "$target" || test -f "$target"
    if [ -f "$target" ] && cmp -s "$source" "$target" &&
        [ "$(stat -f '%u:%g:%p:%f' "$source")" = "$(stat -f '%u:%g:%p:%f' "$target")" ]; then
        return
    fi
    printf 'installing:%s\n' "$2"
    cp -p "$source" "$root/.commonplace-update/file"
    mv -f "$root/.commonplace-update/file" "$target"
    cmp -s "$source" "$target"
    test "$(stat -f '%u:%g:%p:%f' "$source")" = "$(stat -f '%u:%g:%p:%f' "$target")"
    printf 'installed:%s\n' "$2"
}""",
    ]
    q = shlex.quote
    created = set()

    def directories(paths):
        parents = {
            str(parent)
            for path in paths
            for parent in PurePosixPath(path).parents
            if str(parent) != "/"
        }
        for parent in sorted(
            parents, key=lambda path: (len(PurePosixPath(path).parts), path)
        ):
            if parent not in created:
                commands.append("ensure_directory " + q(parent))
                created.add(parent)

    # A declared profile remains authoritative even when service files need repair.
    directories([PROFILE])
    commands.extend(
        [
            'if [ -L "$root'
            + PROFILE
            + '" ]; then echo "installed profile is a symbolic link" >&2; exit 1; fi',
            'if [ -f "$root' + PROFILE + '" ]; then',
            '    IFS= read -r profile < "$root' + PROFILE + '"',
            'elif [ -d "$root/System/Library/LaunchDaemons" ] || [ -d "$root/var/db/launchd.db" ]; then',
            "    profile=apple-services",
            "else",
            "    profile=bootstrap",
            "fi",
            'case "$profile" in bootstrap|apple-services) ;; *) echo "unsupported installed profile" >&2; exit 1 ;; esac',
        ]
    )
    base = system_files()
    directories(base)
    for target in base:
        if target not in ("/sbin/launchd", PROFILE):
            commands.append(f"install_file {q(target)} {q(target)}")
    common_directories = created.copy()
    commands.append('if [ "$profile" = apple-services ]; then')
    directories([*managed, *defaults, *(path + "/.directory" for path in DIRECTORIES)])
    commands.append('chmod 1777 "$root/var/tmp"')
    for target, source in managed.items():
        commands.append(f"install_file {q(source)} {q(target)}")
    for target, source in defaults.items():
        commands.append(
            f'if [ ! -e "$root{target}" ] && [ ! -L "$root{target}" ]; then install_file {q(source)} {q(target)}; fi'
        )
    commands.append("else")
    for target in ("/sbin/launchd", PROFILE):
        commands.append(f"install_file {q(target)} {q(target)}")
    commands.append("fi")
    created = common_directories
    directories(["/var/log/.directory", "/var/run/.directory"])
    # Account records and every existing configuration file are preserved.
    configuration = ROOT / "userland/darwin/etc"
    for source in sorted(configuration.rglob("*")):
        if not source.is_file():
            continue
        target = "/etc/" + source.relative_to(configuration).as_posix()
        if target in IDENTITY_FILES:
            continue
        directories([target])
        commands.append(
            f'if [ ! -e "$root{target}" ] && [ ! -L "$root{target}" ]; then install_file {q(target)} {q(target)}; fi'
        )
    for target, link in system_symlinks().items():
        commands.extend(
            [
                f'test ! -e "$root{target}" || test -L "$root{target}"',
                f'rm -f "$root{target}"',
                f'ln -s {q(link)} "$root{target}"',
                f'test -L "$root{target}" && test -e "$root{target}"',
            ]
        )
    commands.extend(
        [
            'chroot "$root" /bin/sh -c \'set -eu; test "$(id -u)" = 0; /bin/echo installed-runtime-verified\'',
            'rmdir "$root/.commonplace-update"',
            'printf "system-profile:%s\\n" "$profile"',
            "sync",
            'umount "$root"',
            "fsck_hfs -fn -c 16m /dev/rcp1",
        ]
    )
    return commands
