"""Shared QEMU machine definition for bounded and interactive boots."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOADER = ROOT / "build/boot/loader.elf"
KERNEL = ROOT / "build/xnu/obj/DEVELOPMENT_X86_64/kernel.development"
ROOT_IMAGE = ROOT / "build/rootfs/root.hfs"
DATA_DISK = ROOT / "build/disks/data.hfs"
SYSTEM_DISK = ROOT / "build/disks/system.hfs"


def command_for(
    modules, memory, disk=None, bounded=True, system_disk=None, disk_root=False
):
    # Invariant TSC exposes timer frequencies through CPUID 0x40000010.
    command = [
        "qemu-system-x86_64",
        "-accel",
        "kvm",
        "-machine",
        "q35",
        "-cpu",
        "host,+invtsc,vmware-cpuid-freq=on",
        "-m",
        str(memory),
        "-smp",
        "1",
        "-kernel",
        str(LOADER),
        "-initrd",
        ",".join(str(p) for p in modules),
        "-display",
        "none",
    ]
    if disk_root:
        if system_disk is None or len(modules) != 1:
            raise ValueError(
                "disk root requires a system disk and only a kernel module"
            )
        command += ["-append", "root=cp1"]
    if bounded:
        command += ["-no-reboot", "-no-shutdown"]
    if disk is not None or system_disk is not None:
        command += ["-device", "piix3-ide,id=storage,addr=05.0"]
        for unit, name, path in ((0, "data", disk), (1, "system", system_disk)):
            if path is None:
                continue
            if "," in str(path):
                raise ValueError("disk paths cannot contain commas")
            command += [
                "-drive",
                f"if=none,id={name},file={path},format=raw,cache=writeback",
                "-device",
                f"ide-hd,drive={name},bus=storage.0,unit={unit},logical_block_size=512,physical_block_size=512",
            ]
    return command
