"""Shared QEMU machine definition for bounded and interactive boots."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOADER = ROOT / 'build/boot/loader.elf'
KERNEL = ROOT / 'build/xnu/obj/DEVELOPMENT_X86_64/kernel.development'
ROOT_IMAGE = ROOT / 'build/rootfs/root.hfs'
DATA_DISK = ROOT / 'build/disks/data.hfs'


def command_for(modules, memory, disk=None, bounded=True):
    # Invariant TSC exposes timer frequencies through CPUID 0x40000010.
    command = [
        'qemu-system-x86_64', '-accel', 'kvm', '-machine', 'q35',
        '-cpu', 'host,+invtsc,vmware-cpuid-freq=on', '-m', str(memory), '-smp', '1',
        '-kernel', str(LOADER), '-initrd', ','.join(str(p) for p in modules),
        '-display', 'none',
    ]
    if bounded:
        command += ['-no-reboot', '-no-shutdown']
    if disk is not None:
        command += ['-device', 'piix3-ide,id=storage,addr=05.0',
                    '-drive', f'if=none,id=data,file={disk},format=raw,cache=writeback',
                    '-device', 'ide-hd,drive=data,bus=storage.0,logical_block_size=512,physical_block_size=512']
    return command
