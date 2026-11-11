#!/usr/bin/env bash
set -euo pipefail
release_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python3 "$release_root/scripts/verify-release.py" "$release_root"
exec python3 "$release_root/scripts/console-qemu.py" "$@"
