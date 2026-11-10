#!/usr/bin/env bash
set -euo pipefail
exec clang --target=x86_64-apple-darwin15 "$@"
