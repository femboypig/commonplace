"""Files and default policies shared by service installation and offline updates."""

from pathlib import Path
import plistlib
from rootfs_image import ROOT

PROFILE = "/usr/share/commonplace/profile"
DIRECTORIES = (
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
)


def service_files():
    files = {
        target: ROOT / "build/darwin/bin" / name
        for name, target in (
            ("apple-launchd", "/sbin/launchd"),
            ("launchctl", "/bin/launchctl"),
            ("notifyd", "/usr/sbin/notifyd"),
            ("syslogd", "/usr/sbin/syslogd"),
            ("syslog", "/usr/bin/syslog"),
            ("first-login", "/usr/libexec/commonplace/first-login"),
        )
    }
    files["/usr/libexec/commonplace/boot"] = ROOT / "userland/darwin/services/boot.sh"
    files[PROFILE] = ROOT / "userland/darwin/services/profile"
    return files


def service_defaults(directory, *, console_login=True):
    directory = Path(directory)
    files = {}

    def install_plist(value, target):
        host = directory / Path(target).name
        host.write_bytes(plistlib.dumps(value))
        files[target] = host

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
        value = plistlib.loads((ROOT / "sources" / component / relative).read_bytes())
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

    configuration = directory / "syslog.conf"
    configuration.write_text("*.*\t/var/log/system.log\n")
    files["/etc/syslog.conf"] = configuration
    files["/usr/libexec/commonplace/console"] = (
        ROOT
        / "userland/darwin/services"
        / ("login-console.sh" if console_login else "console.sh")
    )
    return files


def service_mode(target):
    if target == PROFILE or target.endswith(".plist") or target == "/etc/syslog.conf":
        return "644"
    return "755"
