"""Shared QEMU machine definition for bounded and interactive boots."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOADER = ROOT / 'build/boot/loader.elf'
KERNEL = ROOT / 'build/xnu/obj/DEVELOPMENT_X86_64/kernel.development'
ROOT_IMAGE = ROOT / 'build/rootfs/root.hfs'


def command_for(modules, memory):
    # Invariant TSC exposes timer frequencies through CPUID 0x40000010.
    return [
        'qemu-system-x86_64', '-accel', 'kvm', '-machine', 'q35',
        '-cpu', 'host,+invtsc,vmware-cpuid-freq=on', '-m', str(memory), '-smp', '1',
        '-kernel', str(LOADER), '-initrd', ','.join(str(p) for p in modules),
        '-display', 'none', '-no-reboot', '-no-shutdown',
    ]
