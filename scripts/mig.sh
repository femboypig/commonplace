#!/usr/bin/env bash
set -euo pipefail
tool_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export MIGCC="$tool_root/bin/x86_64-apple-darwin15-clang"
export MIGCOM="$tool_root/libexec/migcom"
# Apple defaults to the output architecture of /usr/bin/arch on the host.
# Set it explicitly and propagate failures from the preprocessor pipeline.
exec bash -o pipefail "$tool_root/libexec/mig-driver" -arch x86_64 "$@"
