"""Assemble a bootable native Apple service-manager image."""

import plistlib
import subprocess
import tempfile
from pathlib import Path
from rootfs_image import ROOT, build_image


def build_service_image(image, size_mib=96, persistent=True):
    image = Path(image)
    build_image(image, size_mib, persistent=persistent)
    hfs = ROOT / "toolchain/bin/hfsplus"

    def run(*arguments):
        subprocess.run([str(hfs), str(image), *map(str, arguments)], check=True)

    for path in (
        "/Library",
        "/Library/LaunchDaemons",
        "/System/Library/LaunchDaemons",
        "/System/Library/CoreServices",
        "/var/db",
        "/var/db/launchd.db",
        "/var/db/launchd.db/com.apple.launchd",
        "/var/tmp",
        "/var/folders",
        "/var/log/asl",
        "/usr/libexec",
        "/usr/libexec/commonplace",
        "/etc/mach_init.d",
    ):
        run("mkdir", path)
    run("chmod", "1777", "/var/tmp")
    for name, target in (
        ("apple-launchd", "/sbin/launchd"),
        ("launchctl", "/bin/launchctl"),
        ("notifyd", "/usr/sbin/notifyd"),
        ("syslogd", "/usr/sbin/syslogd"),
        ("syslog", "/usr/bin/syslog"),
    ):
        run("add", ROOT / "build/darwin/bin" / name, target)
        run("chmod", "755", target)
    run(
        "add",
        ROOT / "userland/darwin/services/console.sh",
        "/usr/libexec/commonplace/console",
    )
    run("chmod", "755", "/usr/libexec/commonplace/console")
    run(
        "add",
        ROOT / "userland/darwin/services/boot.sh",
        "/usr/libexec/commonplace/boot",
    )
    run("chmod", "755", "/usr/libexec/commonplace/boot")
    with tempfile.TemporaryDirectory(
        dir=image.parent, prefix=".services-"
    ) as directory:
        temporary = Path(directory)

        def install_plist(value, target):
            host = temporary / Path(target).name
            host.write_bytes(plistlib.dumps(value))
            run("add", host, target)
            run("chmod", "644", target)

        install_plist(
            dict(
                Label="org.commonplace.console",
                ProgramArguments=["/bin/sh", "/usr/libexec/commonplace/console"],
                KeepAlive={"PathState": {"/var/run/commonplace.ready": True}},
                ThrottleInterval=1,
                StandardInPath="/dev/console",
                StandardOutPath="/dev/console",
                StandardErrorPath="/dev/console",
            ),
            "/System/Library/LaunchDaemons/org.commonplace.console.plist",
        )
        install_plist(
            dict(
                Label="org.commonplace.boot",
                ProgramArguments=["/bin/sh", "/usr/libexec/commonplace/boot"],
                RunAtLoad=True,
                StandardOutPath="/dev/console",
                StandardErrorPath="/dev/console",
            ),
            "/System/Library/LaunchDaemons/org.commonplace.boot.plist",
        )
        for component, relative in (
            ("libnotify", "notifyd/com.apple.notifyd.plist"),
            ("syslog_services", "syslogd.tproj/com.apple.syslogd.plist"),
        ):
            value = plistlib.loads(
                (ROOT / "sources" / component / relative).read_bytes()
            )
            # The published manager uses shared-memory transactions; our newer vproc
            # runtime uses XNU dirty tracking. Keep these essential services alive
            # explicitly until both transaction protocols are integrated.
            value.pop("EnableTransactions", None)
            value["KeepAlive"] = True
            value["RunAtLoad"] = True
            value["StandardErrorPath"] = "/var/log/" + value["Label"] + ".stderr"
            install_plist(value, "/System/Library/LaunchDaemons/" + Path(relative).name)
        install_plist(
            dict(
                ProductName="commonplace",
                ProductVersion="0.1.0",
                ProductBuildVersion="development",
            ),
            "/System/Library/CoreServices/SystemVersion.plist",
        )
        configuration = temporary / "syslog.conf"
        configuration.write_text("*.*\t/var/log/system.log\n")
        run("add", configuration, "/etc/syslog.conf")
        run("chmod", "644", "/etc/syslog.conf")
