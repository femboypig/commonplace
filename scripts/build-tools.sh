#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"
jobs=${JOBS:-2}
[[ $jobs =~ ^[1-9][0-9]*$ ]] || { echo 'JOBS must be a positive integer' >&2; exit 1; }
mkdir -p build/cctools build/mig toolchain/bin toolchain/libexec

run_logged() {
    local log=$1
    shift
    if ! "$@" > "$log" 2>&1; then
        tail -60 "$log" >&2
        return 1
    fi
}

echo 'building cctools and ld64'
(
    cd build/cctools
    run_logged configure.log "$project_root/sources/cctools/cctools/configure" \
        --prefix="$project_root/toolchain" --target=x86_64-apple-darwin15 \
        --with-llvm-config=no
    run_logged build.log make -j"$jobs"
    run_logged install.log make install
)

echo 'building apple mach interface generator'
(
    cd build/mig
    mig_source="$project_root/sources/bootstrap_cmds/migcom.tproj"
    compat="$project_root/sources/mig_host_compat/compat/non_apple"
    bison -y -d -o y.tab.c "$mig_source/parser.y"
    flex -o lex.yy.c "$mig_source/lexxer.l"
    # Host-only Mach declarations come from the cross-platform MIG port.
    # The generator itself is Apple's pinned 96.20.2 release.
    sources=()
    for source in error global header mig routine server statement string type user utils; do
        sources+=("$mig_source/$source.c")
    done
    run_logged build.log clang -std=gnu99 -O2 -include sys/types.h \
        -D__private_extern__= '-DMIG_VERSION="bootstrap_cmds-96.20.2"' \
        -I. -I"$mig_source" -I"$compat" "${sources[@]}" y.tab.c lex.yy.c \
        -o "$project_root/toolchain/libexec/migcom"
    # The Apple driver uses /usr/bin/arch, absent on current Arch Linux.
    sed 's|arch=`/usr/bin/arch`|arch=x86_64|' "$mig_source/mig.sh" \
        > "$project_root/toolchain/libexec/mig-driver"
)

install -m 755 scripts/target-clang.sh toolchain/bin/x86_64-apple-darwin15-clang
install -m 755 scripts/mig.sh toolchain/bin/mig
echo "tools installed in $project_root/toolchain"
