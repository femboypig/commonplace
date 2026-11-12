"""Keep the persistent root on a distinct device and out of RAM modules."""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "machine", ROOT / "scripts/qemu_machine.py"
)
machine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(machine)


class QemuMachineTest(unittest.TestCase):
    def test_disk_root_and_recovery(self):
        command = machine.command_for(
            ["kernel"], 512, "data.hfs", system_disk="system.hfs", disk_root=True
        )
        self.assertIn("root=cp1", command)
        self.assertIn("kernel", command)
        devices = [
            command[index + 1]
            for index, item in enumerate(command)
            if item == "-device"
        ]
        self.assertTrue(
            any("drive=data" in item and "unit=0" in item for item in devices)
        )
        self.assertTrue(
            any("drive=system" in item and "unit=1" in item for item in devices)
        )
        recovery = machine.command_for(
            ["kernel", "root.hfs"], 512, system_disk="system.hfs"
        )
        self.assertNotIn("-append", recovery)
        self.assertIn("kernel,root.hfs", recovery)

    def test_invalid_root_configuration(self):
        with self.assertRaises(ValueError):
            machine.command_for(["kernel"], 512, disk_root=True)
        with self.assertRaises(ValueError):
            machine.command_for(
                ["kernel", "ram"], 512, system_disk="system", disk_root=True
            )
        with self.assertRaises(ValueError):
            machine.command_for(["kernel"], 512, system_disk="unsafe,path")
