#!/usr/bin/env python3
"""Run a bounded KVM boot and preserve serial output and CPU state."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

from qemu_monitor import Monitor

ROOT = Path(__file__).resolve().parent.parent


def boot_state(log):
    return {
        'kernel_entered': 'Darwin Kernel Version 15.6.0:' in log,
        'platform_started': 'commonplace: q35 bootstrap platform started' in log,
        'waiting_for_root': 'Still waiting for root device' in log,
        'fatal': any(marker in log for marker in
                     ('panic(cpu ', 'Panic initiated,', 'boot stopped:')),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=15)
    parser.add_argument('--memory', type=int, default=1024, help='guest memory in MiB')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/boot',
                        help='directory for this run\'s logs and diagnostics')
    options = parser.parse_args()
    if not 1 <= options.seconds <= 3600 or not 512 <= options.memory <= 8192:
        parser.error('seconds must be 1..3600 and memory must be 512..8192 MiB')
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    kernel = ROOT / 'build/xnu/obj/DEVELOPMENT_X86_64/kernel.development'
    loader = ROOT / 'build/boot/loader.elf'
    serial = output / 'serial.log'
    for artifact in (kernel, loader):
        if not artifact.is_file():
            parser.error(f'missing artifact: {artifact}')
    # Invariant TSC lets QEMU expose real timer frequencies in CPUID 0x40000010.
    with tempfile.TemporaryDirectory(prefix='commonplace-qmp-') as directory:
        path = Path(directory) / 'monitor'
        command = [
            'qemu-system-x86_64', '-accel', 'kvm', '-machine', 'q35',
            '-cpu', 'host,+invtsc,vmware-cpuid-freq=on',
            '-m', str(options.memory), '-smp', '1', '-kernel', str(loader),
            '-initrd', str(kernel), '-display', 'none',
            '-serial', f'file:{output / "serial.log"}',
            '-qmp', f'unix:{path},server=on,wait=off', '-no-reboot', '-no-shutdown',
        ]
        with (output / 'qemu.stderr.log').open('w') as errors:
            process = subprocess.Popen(command, cwd=ROOT, stderr=errors)
            monitor = None
            try:
                monitor = Monitor(path, process)
                deadline = time.monotonic() + options.seconds
                while time.monotonic() < deadline and process.poll() is None:
                    if serial.exists() and boot_state(serial.read_text(errors='replace'))['fatal']:
                        break
                    time.sleep(min(0.25, max(0, deadline - time.monotonic())))
                diagnostics = {'command': command, 'seconds': options.seconds,
                               'status': monitor.command('query-status'),
                               'sha256': {str(p.relative_to(ROOT)):
                                          hashlib.sha256(p.read_bytes()).hexdigest()
                                          for p in (loader, kernel)}}
                monitor.command('stop')
                diagnostics['boot'] = boot_state(serial.read_text(errors='replace'))
                for name, request in {
                    'registers': 'info registers', 'instructions': 'x/12i $rip',
                    'stack': 'x/48gx $rsp', 'frames': 'x/32gx $rbp',
                }.items():
                    diagnostics[name] = monitor.inspect(request)
                (output / 'diagnostics.json').write_text(json.dumps(diagnostics, indent=2) + '\n')
            finally:
                if monitor:
                    monitor.close()
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    log = serial.read_text(errors='replace').splitlines()
    if len(log) > 100:
        log = log[:80] + [f'... full output: {serial} ...'] + log[-20:]
    print('\n'.join(log))
    print(f'boot observation finished; diagnostics: {output / "diagnostics.json"}')
    if diagnostics['boot']['fatal']:
        raise SystemExit('boot failed: kernel panic or loader failure')
    if not diagnostics['boot']['kernel_entered']:
        raise SystemExit('boot failed: kernel version banner not reached')
    if not diagnostics['boot']['platform_started']:
        raise SystemExit('boot failed: q35 platform did not start')
    print('bootstrap milestones reached: darwin kernel and q35 platform')


if __name__ == '__main__':
    main()
