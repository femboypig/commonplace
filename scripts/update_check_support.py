"""Host entry points used by native maintenance integration checks."""

import subprocess
import sys
from rootfs_image import ROOT


def run_update(system, *options, success=True):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/update-system.py"),
            "--path",
            str(system),
            *options,
        ],
        capture_output=True,
        text=True,
    )
    if (result.returncode == 0) != success:
        raise ValueError(result.stdout + result.stderr)
    return result
