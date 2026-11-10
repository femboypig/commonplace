#!/usr/bin/env bash
set -euo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"
mkdir -p build/profile-runtime toolchain/lib
profile_source="$project_root/sources/compiler_rt/lib/profile"
resource_dir=$(clang -print-resource-dir)
objects=()
for source in InstrProfiling InstrProfilingBuffer InstrProfilingPlatformDarwin; do
    object="$project_root/build/profile-runtime/$source.o"
    "$project_root/toolchain/bin/x86_64-apple-darwin15-clang" \
        -std=gnu99 -O2 -ffreestanding -fno-builtin -fno-stack-protector \
        -mkernel -msoft-float -mno-red-zone -nostdinc \
        -isystem "$resource_dir/include" -I"$project_root/compat/runtime" \
        -I"$profile_source" -c "$profile_source/$source.c" -o "$object"
    objects+=("$object")
done
"$project_root/toolchain/bin/x86_64-apple-darwin15-libtool" -static \
    -o "$project_root/toolchain/lib/libkernel_profile.a" "${objects[@]}"
