#!/usr/bin/env bash
set -euo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"
mkdir -p build/boot
sources=(image tree memory multiboot arguments runtime main platform/serial platform/x86 platform/entry)
objects=()
for source in "${sources[@]}"; do
    extension=c
    if [[ $source == platform/entry ]]; then extension=S; fi
    object="build/boot/${source//\//-}.o"
    clang --target=i686-unknown-none-elf -std=c11 -O2 -g \
        -Wall -Wextra -Werror -ffreestanding -fno-builtin \
        -fno-pic -fno-pie -fno-stack-protector -mno-sse -mno-mmx \
        -Iboot -Isources/xnu/pexpert -c "boot/$source.$extension" -o "$object"
    objects+=("$object")
done
ld.lld -m elf_i386 --fatal-warnings -T boot/platform/loader.ld \
    -o build/boot/loader.elf "${objects[@]}"
