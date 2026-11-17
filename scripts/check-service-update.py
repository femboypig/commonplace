#!/usr/bin/env python3
"""Verify service updates and rollback with real PAM users and local configuration."""

from datetime import datetime, timezone
import hashlib
import json
import plistlib
import re
import shutil
import subprocess
from rootfs_image import ROOT
from service_image import build_service_image
from guest_console import Console, PROMPT
from qemu_machine import command_for, KERNEL
from update_check_support import run_update
from recovery_session import run_command
from qemu_machine import ROOT_IMAGE

ROOT_PASSWORD = "Update-root-passphrase-2026!"
USER_PASSWORD = "Update-user-passphrase-2026!"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boot(image, directory, *, initial=False, updated=False):
    console = Console(
        command_for([KERNEL], 1024, bounded=False, system_disk=image, disk_root=True)
        + ["-serial", "mon:stdio"],
        directory,
    )
    try:
        if initial:
            console.expect(
                rb"commonplace first boot: set the root password", seconds=180
            )
            console.change_password(ROOT_PASSWORD)
        console.login("root", ROOT_PASSWORD)
        if initial:
            console.command(
                "cp /etc/master.passwd /tmp/accounts; printf '%s\\n' 'tester:*:501:20::0:0:test user:/home/tester:/bin/sh' >> /tmp/accounts; pwd_mkdb -p /tmp/accounts; mkdir /home /home/tester; chown tester:staff /home/tester; chmod 700 /home/tester",
                rb"pwd_mkdb",
            )
            console.sendline("passwd tester")
            console.change_password(USER_PASSWORD)
            console.expect(PROMPT)
            console.command(
                "echo '# local PAM policy' >> /etc/pam.d/login; echo '# local logging policy' >> /etc/syslog.conf; echo retained > /root/private-file; echo configured > /etc/site-setting",
                rb"\Aecho",
            )
        console.command(
            "printf abcdef > /tmp/cmp-a; printf abXdef > /tmp/cmp-b; cmp -s /tmp/cmp-a /tmp/cmp-b; echo different-status:$?; cmp -s -n 2 /tmp/cmp-a /tmp/cmp-b; echo limit-status:$?; cmp -s -i 3:3 /tmp/cmp-a /tmp/cmp-b; echo skip-status:$?",
            rb"different-status:1\nlimit-status:0\nskip-status:0",
        )
        console.command(
            "launchctl list", rb"com.apple.notifyd[\s\S]*|com.apple.syslogd[\s\S]*"
        )
        console.command(
            "cat /root/local-service /root/private-file /etc/site-setting",
            rb"\nlocal-service\nretained\nconfigured\n",
        )
        if updated:
            console.command(
                "test -u /usr/bin/passwd; echo setuid-status:$?", rb"setuid-status:0"
            )
            console.command(
                "/bin/echo installed-ok; /root/linked-original; echo linked-status:$?",
                rb"\ninstalled-ok\nlinked-status:1\n",
            )
            console.command(
                "test -x /usr/libexec/commonplace/boot; cat /usr/share/commonplace/profile",
                rb"\napple-services\n",
            )
            console.command(
                "test -f /System/Library/LaunchDaemons/com.apple.syslogd.plist; echo policy-status:$?",
                rb"policy-status:0",
            )
        console.sendline("exit")
        prompt = rb"[A-Za-z0-9.-]+:[^\n]+ tester\$ "
        console.login("tester", USER_PASSWORD, prompt)
        console.sendline(
            "id -u; test ! -r /etc/master.passwd; echo private-status:$?; echo user-data > retained; cat retained"
        )
        response = console.expect(prompt)
        if not re.search(rb"\n501\nprivate-status:0\nuser-data\n", response):
            raise ValueError("update changed user identity, permissions or home access")
        console.sendline("exit")
        console.login("root", ROOT_PASSWORD)
        console.command(
            "test $(stat -f %u /home/tester/retained) = 501; echo owner-status:$?",
            rb"owner-status:0",
        )
        if initial:
            console.command(
                "cp /bin/false /root/linked-original; rm /bin/echo; ln /root/linked-original /bin/echo",
                rb"\Acp",
            )
        console.poweroff()
    finally:
        console.close()


def main():
    directory = (
        ROOT
        / "build/service-update-checks"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    directory.mkdir(parents=True)
    image = directory / "system.hfs"
    build_service_image(image, 128)
    factory_check = directory / "factory-check"
    factory_check.mkdir()
    run_command(factory_check, ROOT_IMAGE, image,
        "fsck_hfs -fn -c 16m /dev/rcp1 && echo factory-image-verified")
    hfs = str(ROOT / "toolchain/bin/hfsplus")

    def run(*args):
        subprocess.run([hfs, str(image), *map(str, args)], check=True)

    def extract(target, label):
        file = directory / label
        run("extract", target, file)
        return file.read_bytes()

    local = directory / "local.plist"
    local.write_bytes(
        plistlib.dumps(
            dict(
                Label="org.commonplace.local",
                RunAtLoad=True,
                ProgramArguments=[
                    "/bin/sh",
                    "-c",
                    "echo local-service > /root/local-service",
                ],
            )
        )
    )
    run("add", local, "/Library/LaunchDaemons/org.commonplace.local.plist")
    run("chmod", "644", "/Library/LaunchDaemons/org.commonplace.local.plist")
    boot(image, directory / "initial.log", initial=True)
    original = directory / "original.hfs"
    shutil.copyfile(image, original)
    before = digest(original)
    preserved = (
        "/etc/master.passwd",
        "/etc/passwd",
        "/etc/group",
        "/etc/pam.d/login",
        "/etc/syslog.conf",
        "/usr/libexec/commonplace/console",
        "/System/Library/LaunchDaemons/org.commonplace.console.plist",
        "/Library/LaunchDaemons/org.commonplace.local.plist",
    )
    retained = {
        path: extract(path, "saved-" + str(index))
        for index, path in enumerate(preserved)
    }
    # Recognize installations created before the profile marker existed.
    run("rm", "/usr/share/commonplace/profile")
    for path in ("/sbin/launchd", "/usr/sbin/notifyd"):
        run("add", ROOT / "build/userland/false", path)
    run("chmod", "755", "/usr/bin/passwd")
    run("rm", "/usr/libexec/commonplace/boot")
    run("rm", "/System/Library/LaunchDaemons/com.apple.syslogd.plist")
    damaged = digest(image)
    run_update(image)
    backups = list(directory.glob("system.hfs.previous-*"))
    if len(backups) != 1 or digest(backups[0]) != damaged:
        raise ValueError("service update failed to preserve the previous disk")
    for index, path in enumerate(preserved):
        if extract(path, "updated-" + str(index)) != retained[path]:
            raise ValueError("update changed local configuration: " + path)
    if (
        extract("/sbin/launchd", "updated-launchd")
        != (ROOT / "build/darwin/bin/apple-launchd").read_bytes()
    ):
        raise ValueError("service update did not install the Apple manager")
    boot(image, directory / "updated.log", updated=True)
    run_update(image, "--restore", str(original))
    if digest(image) != before:
        raise ValueError("rollback did not restore the exact original service disk")
    boot(image, directory / "restored.log")
    summary = {"passed": True, "preserved": list(preserved), "original_sha256": before}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        "service update, authenticated users, local policies and rollback passed: "
        + str(directory)
    )


if __name__ == "__main__":
    main()
