#!/usr/bin/env python3
"""Exercise first-boot password setup, Apple PAM login and unprivileged sessions."""

from datetime import datetime, timezone
import json
import re
import subprocess
from darwin_build import ROOT, OUT, compile_source, link_program
from guest_console import Console, PROMPT
from qemu_machine import command_for, KERNEL
from service_image import build_service_image

# Fixed credentials belong only to fresh disposable test images.
ROOT_PASSWORD = "Root-check-passphrase-2026!"
USER_PASSWORD = "User-check-passphrase-2026!"
NEW_PASSWORD = "Changed-check-passphrase-2026!"


def main():
    directory = (
        ROOT
        / "build/login-checks"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    directory.mkdir(parents=True)
    image = directory / "system.hfs"
    build_service_image(image)
    hfs = str(ROOT / "toolchain/bin/hfsplus")
    for name, library in (
        ("password_runtime", "libcrypt.dylib"),
        ("login_policy", "libpam.2.dylib"),
    ):
        obj = compile_source(
            ROOT / "tests/guest" / (name + ".c"),
            OUT / "obj/tests" / (name + ".o"),
            ["-I" + str(ROOT / "userland/darwin/password")],
        )
        probe = directory / name
        link_program(probe, [obj], [OUT / "system" / library])
        subprocess.run([hfs, str(image), "add", str(probe), "/bin/" + name], check=True)
        subprocess.run([hfs, str(image), "chmod", "755", "/bin/" + name], check=True)
    command = command_for(
        [KERNEL], 1024, bounded=False, system_disk=image, disk_root=True
    ) + [
        "-serial",
        "mon:stdio",
        "-qmp",
        "unix:" + str(directory / "qmp") + ",server=on,wait=off",
    ]
    for phase in ("setup", "cold"):
        console = Console(command, directory / (phase + ".log"))
        try:
            if phase == "setup":
                console.expect(
                    rb"commonplace first boot: set the root password", seconds=180
                )
                console.expect(rb"New password:")
                console.sendline("")
                console.expect(rb"Password unchanged")
                console.expect(rb"commonplace first boot: set the root password")
                console.change_password(ROOT_PASSWORD)
            console.login("root", ROOT_PASSWORD)
            console.command("id -u; id -g", rb"\n0\n0\n")
            if phase == "setup":
                console.command(
                    "password_runtime", rb"native password hashing:.*passed"
                )
                console.command(
                    "test ! -e /etc/commonplace.setup-required; echo setup-status:$?",
                    rb"setup-status:0",
                )
                console.command(
                    "cp /etc/master.passwd /tmp/accounts; printf '%s\\n' 'tester:*:501:20::0:0:test user:/home/tester:/bin/sh' 'expired:*:502:20::0:1:expired:/home/tester:/bin/sh' 'changed:*:503:20::1:0:changed:/home/tester:/bin/sh' >> /tmp/accounts; pwd_mkdb -p /tmp/accounts; echo account-status:$?",
                    rb"account-status:0",
                )
                console.command(
                    "mkdir /home /home/tester; chown tester:staff /home/tester; chmod 700 /home/tester",
                    rb"\Amkdir",
                )
                console.sendline("passwd tester")
                console.change_password(USER_PASSWORD)
                console.expect(PROMPT)
                console.command("login_policy", rb"native login policy:.*passed")
                console.command(
                    "printf '%s\\n' '#!/bin/sh' 'echo \"vipwtest:*:504:20::0:0:vipw test:/home/tester:/bin/sh\" >> \"$1\"' > /tmp/account-editor; chmod 700 /tmp/account-editor; EDITOR=/tmp/account-editor vipw; id -u vipwtest",
                    rb"\n504\n",
                )
                console.command(
                    "printf '%s\\n' '#!/bin/sh' 'sed -i \"\" s/^vipwtest:/vipwuser:/ \"$1\"' > /tmp/account-editor; EDITOR=/tmp/account-editor vipw; id -u vipwuser",
                    rb"\n504\n",
                )
                console.command(
                    "EDITOR=/bin/true vipw; echo unchanged-status:$?",
                    rb"unchanged[\s\S]*unchanged-status:0",
                )
            console.sendline("exit")
            console.expect(rb"login: ")
            console.sendline("tester")
            console.expect(rb"Password:")
            console.sendline("incorrect-password")
            console.expect(rb"Login incorrect")
            user_prompt = rb"[A-Za-z0-9.-]+:[^\n]+ tester\$ "
            console.login(
                "tester",
                USER_PASSWORD if phase == "setup" else NEW_PASSWORD,
                user_prompt,
            )
            console.sendline("id -u; id -g; id -G; pwd")
            response = console.expect(user_prompt)
            if not re.search(rb"\n501\n20\n20\n/home/tester\n", response):
                raise ValueError("login did not establish the expected user identity")
            console.sendline("login_policy --identity")
            if b"privilege separation passed" not in console.expect(user_prompt):
                raise ValueError(
                    "login did not establish restricted kernel credentials"
                )
            console.sendline(
                "test ! -r /etc/master.passwd && test ! -x /root; echo private-status:$?"
            )
            if b"private-status:0" not in console.expect(user_prompt):
                raise ValueError("user can access protected account or root files")
            console.sendline("passwd root; echo other-user-status:$?")
            if not re.search(rb"other-user-status:[1-9]", console.expect(user_prompt)):
                raise ValueError("user changed another account")
            if phase == "setup":
                console.sendline("passwd; echo rejected-status:$?")
                console.expect(rb"Old password:")
                console.sendline("incorrect-password")
                if not re.search(
                    rb"rejected-status:[1-9]", console.expect(user_prompt)
                ):
                    raise ValueError(
                        "password update accepted an incorrect old password"
                    )
                console.sendline("passwd; echo cancelled-status:$?")
                console.expect(rb"Old password:")
                console.sendline(USER_PASSWORD)
                console.expect(rb"New password:")
                console.sendline("")
                if not re.search(
                    rb"cancelled-status:[1-9]", console.expect(user_prompt)
                ):
                    raise ValueError("cancelled password update reported success")
                console.sendline("passwd")
                console.expect(rb"Old password:")
                console.sendline(USER_PASSWORD)
                console.expect(rb"New password:")
                console.sendline("x" * 129)
                console.expect(rb"Password must not exceed 128 bytes")
                console.change_password(NEW_PASSWORD)
                console.expect(user_prompt)
            console.sendline("echo unprivileged-data > retained; id -u")
            if not re.search(rb"\n501\n", console.expect(user_prompt)):
                raise ValueError("password update changed the real uid")
            console.sendline("exit")
            console.login("root", ROOT_PASSWORD)
            console.command("cat /home/tester/retained", rb"\nunprivileged-data\n")
            console.poweroff()
        except Exception:
            from qemu_monitor import Monitor

            monitor = Monitor(directory / "qmp", console.process)
            try:
                monitor.command("stop")
                (directory / (phase + "-diagnostics.json")).write_text(
                    json.dumps(
                        {
                            "registers": monitor.inspect("info registers"),
                            "frames": monitor.inspect("x/32gx $rbp"),
                            "instructions": monitor.inspect("x/12i $rip"),
                        },
                        indent=2,
                    )
                    + "\n"
                )
            finally:
                monitor.close()
            raise
        finally:
            console.close()
        log = (directory / (phase + ".log")).read_bytes()
        if any(
            secret.encode() in log
            for secret in (ROOT_PASSWORD, USER_PASSWORD, NEW_PASSWORD)
        ):
            raise ValueError("console echoed a password")
    (directory / "summary.json").write_text(
        json.dumps({"passed": True, "phases": ["setup", "cold"]}, indent=2) + "\n"
    )
    print("native Apple login and password lifecycle passed: " + str(directory))


if __name__ == "__main__":
    main()
