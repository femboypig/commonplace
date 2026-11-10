#!/usr/bin/env bash
set -euo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"
mkdir -p build/rootfs-tools toolchain/bin
mkdir -p build/hfsprogs-source
cp -a sources/hfsprogs/. build/hfsprogs-source/
for patch in patches/hfsprogs/*.patch; do
    patch --batch --fuzz=0 -p1 -d build/hfsprogs-source -i "$project_root/$patch"
done
for name in hfs_endian makehfs newfs_hfs; do
    gcc -std=gnu11 -O2 -g -Wall -Wextra -Wno-unused-parameter \
        -DLINUX=1 -DBSD=1 -DDEBUG_BUILD=0 -D_FILE_OFFSET_BITS=64 \
        '-DVERSION="540.1.linux3"' -Isources/hfsprogs/include \
        -c "build/hfsprogs-source/newfs_hfs.tproj/$name.c" \
        -o "build/rootfs-tools/$name.o"
done
gcc -o toolchain/bin/newfs_hfs build/rootfs-tools/{hfs_endian,makehfs,newfs_hfs}.o -lcrypto
hfs_sources=(btree catalog extents fastunicodecompare flatfile hfslib rawfile utility volume hfs)
objects=(sources/hfs_tools/common/abstractfile.c)
for name in "${hfs_sources[@]}"; do
    objects+=("sources/hfs_tools/hfs/$name.c")
done
gcc -std=gnu11 -O2 -g -Wall -Wextra -Wno-unused-parameter \
    -D_FILE_OFFSET_BITS=64 -Isources/hfs_tools/includes \
    "${objects[@]}" -o toolchain/bin/hfsplus
