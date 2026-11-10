#!/usr/bin/env bash
set -euo pipefail
while (($#)); do
    case "$1" in
        -verbose) shift ;;
        -sdk) shift 2 ;;
        -find)
            case "${2:?missing tool name}" in
                dsymutil) command -v dsymutil || command -v llvm-dsymutil ;;
                ctfconvert|ctfmerge|ctf_insert) exit 1 ;;
                *) command -v "$2" ;;
            esac
            exit ;;
        *) echo "unsupported xcrun query: $1" >&2; exit 1 ;;
    esac
done
exit 1
