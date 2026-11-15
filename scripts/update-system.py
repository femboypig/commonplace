#!/usr/bin/env python3
"""Update an offline system through Darwin recovery, retaining a rollback image."""

import argparse
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from offline_image import (
    locked_image as locked_image,
    image_transaction,
    maintenance_signals,
)
from rootfs_image import ROOT
from recovery_session import recovery_image, install_script, run_script
from system_update_plan import prepare_payload, update_commands


def recovery_check(directory, image, update):
    recovery = recovery_image(directory, current_build=update)
    commands = ["set -eu", "fsck_hfs -fn -c 16m /dev/rcp1"]
    if update:
        managed, defaults = prepare_payload(directory, recovery)
        commands.extend(update_commands(managed, defaults))
    commands.append("echo system-image-verified")
    install_script(recovery, directory, "update.sh", "\n".join(commands) + "\n")
    response = run_script(directory, recovery, image, "update.sh")
    if "\nsystem-image-verified\n" not in response:
        raise ValueError(
            "incomplete recovery transaction; diagnostics: " + str(directory)
        )
    profiles = re.findall(
        r"^system-profile:(bootstrap|apple-services)$", response, re.M
    )
    return profiles[-1] if profiles else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=ROOT / "build/disks/system.hfs")
    parser.add_argument(
        "--restore", type=Path, help="restore a previous full system image"
    )
    options = parser.parse_args()
    path = options.path.resolve(strict=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    evidence = ROOT / "build/update-checks" / stamp
    evidence.mkdir(parents=True)
    with image_transaction(path, stamp, restore=options.restore) as transaction:
        profile = recovery_check(
            evidence, transaction.staged, update=not options.restore
        )
    (evidence / "result.json").write_text(
        json.dumps(
            {
                "passed": True,
                "image": str(path),
                "backup": str(transaction.backup),
                "profile": profile,
                "restored_from": str(transaction.source) if options.restore else None,
            },
            indent=2,
        )
        + "\n"
    )
    print("system ready: " + str(path))
    print("previous system: " + str(transaction.backup))
    print("verification: " + str(evidence))


if __name__ == "__main__":
    with maintenance_signals():
        main()
