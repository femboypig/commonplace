#!/usr/bin/env bash
set -euo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
object_root=${1:?missing xnu object directory}
setup="$project_root/build/xnu-source/SETUP"
includes="$project_root/sources/cctools/cctools/include"
host_flags=(-std=gnu99 -O2 -D__private_extern__= -D__DARWIN_UNIX03
    -DHAVE_BCMP=1 -DHAVE_BZERO=1 -DHAVE_BCOPY=1 -DHAVE_INDEX=1 -DHAVE_RINDEX=1
    -include bsd/stdlib.h -include bsd/unistd.h -I"$project_root/compat/host"
    -I"$includes" -I"$includes/foreign")

for tool in kextsymboltool setsegname decomment installfile replacecontents; do
    output="$object_root/SETUP/$tool"
    mkdir -p "$output"
    echo "HOST_CC $tool"
    clang "${host_flags[@]}" "$setup/$tool/$tool.c" \
        "$project_root/build/cctools/libmacho/.libs/libmacho.a" \
        "$project_root/build/cctools/libstuff/.libs/libstuff.a" \
        -luuid -lstdc++ -ldl -lbsd -lm -o "$output/$tool"
done

mkdir -p "$object_root/SETUP/config"
cd "$object_root/SETUP/config"
bison -y -d -o parser.c "$setup/config/parser.y"
flex --header-file=lexer.yy.h -o lexer.yy.c "$setup/config/lexer.l"
source_files=()
for source in externs main mkheaders mkioconf mkmakefile openp searchp; do
    source_files+=("$setup/config/$source.c")
done
clang -std=gnu99 -O2 -DYY_NO_INPUT -I. -I"$setup/config" \
    "${source_files[@]}" lexer.yy.c parser.c -o config
