#!/usr/bin/env python3
"""Run the upstream XNU build with Linux host tools and isolated outputs."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def apply_source_patches(source):
    patches = sorted((ROOT / 'patches/xnu').glob('*.patch'))
    if not patches:
        return
    with tempfile.TemporaryDirectory(dir=ROOT / 'build', prefix='xnu-patches-') as temporary:
        temporary = Path(temporary)
        paths = set()
        for patch in patches:
            for match in re.finditer(r'^--- a/(.+)$', patch.read_text(), re.MULTILINE):
                relative = Path(match[1])
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError(f'invalid patch path: {relative}')
                paths.add(relative)
        for relative in paths:
            destination = temporary / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / 'sources/xnu' / relative, destination)
        for patch in patches:
            subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-d', str(temporary),
                            '-i', str(patch)], check=True, stdout=subprocess.DEVNULL)
        for relative in paths:
            contents = (temporary / relative).read_bytes()
            output = source / relative
            if not output.exists() or output.read_bytes() != contents:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(contents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', choices=('exporthdrs', 'all', 'link'))
    args = parser.parse_args()
    if args.target == 'all' and not shutil.which('csh'):
        parser.error('csh is required for kernel configuration; install the tcsh package')
    source = ROOT / 'build' / 'xnu-source'
    if not source.exists():
        shutil.copytree(ROOT / 'sources' / 'xnu', source, symlinks=True)
    apply_source_patches(source)
    setup = source / 'SETUP' / 'Makefile'
    contents = (ROOT / 'sources/xnu/SETUP/Makefile').read_text()
    start = contents.index('SETUP_SUBDIRS =')
    end = contents.index('ifeq ($(BUILD_JSON_COMPILATION_DATABASE)', start)
    contents = (contents[:start] + 'SETUP_SUBDIRS =\n\n' + contents[end:])
    contents += ('\ndo_build_setup::\n'
                 '\tbash $(COMMONPLACE_ROOT)/scripts/build-xnu-host.sh $(OBJROOT)\n')
    if setup.read_text() != contents:
        setup.write_text(contents)
    for filename, replacements in {
        'Makefile': {
            '$(shell /usr/sbin/sysctl -n hw.physicalcpu)': '$(COMMONPLACE_PHYSICAL_CPUS)',
            '$(shell /usr/sbin/sysctl -n hw.logicalcpu)': '$(COMMONPLACE_LOGICAL_CPUS)',
        },
        'makedefs/MakeInc.top': {
            '$(shell /usr/sbin/sysctl -n hw.memsize)': '$(COMMONPLACE_MEMORY_SIZE)',
        },
        'makedefs/MakeInc.cmd': {
            '/usr/bin/xcrun': '$(COMMONPLACE_ROOT)/scripts/xcrun.sh',
        },
        'libkern/libkern/Makefile': {
            'install $(DATA_INSTALL_FLAGS)': '$(INSTALL) $(DATA_INSTALL_FLAGS)',
            '\tprelink.h\n': '\tprelink.h \\\n\tsection_keywords.h\n',
        },
    }.items():
        contents = (ROOT / 'sources/xnu' / filename).read_text()
        for old, new in replacements.items():
            if old not in contents:
                raise RuntimeError(f'upstream build fragment changed: {filename}')
            contents = contents.replace(old, new)
        output = source / filename
        if output.read_text() != contents:
            output.write_text(contents)
    generator = 'bsd/kern/makekdebugevents.py'
    contents = (ROOT / 'sources/xnu' / generator).read_text().expandtabs(8)
    contents = re.sub(r'^(\s*)print (.+)$', r'\1print(\2)', contents, flags=re.MULTILINE)
    contents = contents.replace("re.compile('", "re.compile(r'")
    output = source / generator
    if output.read_text() != contents:
        output.write_text(contents)
    objects = ROOT / 'build' / 'xnu' / 'obj'
    sdk = ROOT / 'build' / 'sdk'
    sdk.mkdir(parents=True, exist_ok=True)
    tools = ROOT / 'toolchain' / 'bin'
    for tool in ('mig', 'x86_64-apple-darwin15-clang', 'x86_64-apple-darwin15-ld'):
        if not (tools / tool).is_file():
            parser.error('cross tools are missing; run make tools first')
    available_cpus = os.sched_getaffinity(0)
    cores = set()
    for cpu in available_cpus:
        topology = Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
        try:
            cores.add(((topology / 'physical_package_id').read_text().strip(),
                       (topology / 'core_id').read_text().strip()))
        except OSError:
            cores.add(('unknown', str(cpu)))
    variables = {
        'COMMONPLACE_ROOT': ROOT,
        'COMMONPLACE_PHYSICAL_CPUS': len(cores),
        'COMMONPLACE_LOGICAL_CPUS': len(available_cpus),
        'COMMONPLACE_MEMORY_SIZE': os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE'),
        'SRCROOT': source, 'VERSDIR': source, 'OBJROOT': objects,
        'SYMROOT': ROOT / 'build' / 'xnu' / 'sym',
        'DSTROOT': ROOT / 'build' / 'xnu' / 'dst',
        'SDKROOT_RESOLVED': sdk, 'HOST_SDKROOT_RESOLVED': '/',
        'PLATFORM': 'MacOSX', 'PLATFORMPATH': '/', 'SDKVERSION': '10.11',
        'HOST_OS_VERSION': '10.11',
        'MAKEJOBS': '-j2', 'ARCH_CONFIGS': 'X86_64',
        'KERNEL_CONFIGS': 'DEVELOPMENT', 'BUILD_LTO': '0',
        'BUILD_DSYM': '0', 'DO_CTFCONVERT': '0', 'DO_CTFMERGE': '0',
        'DO_CTFMACHO': '0',
        # Keep newer diagnostic groups visible without making them fatal for
        # Apple's older source. The upstream warning policy remains enabled.
        'OTHER_CFLAGS': ' '.join((
            '-UTARGET_OS_MAC',
            '-Wno-error=cast-function-type-mismatch',
            '-Wno-error=c99-designator',
            '-Wno-error=misleading-indentation',
            '-Wno-error=strict-prototypes',
            '-Wno-error=vla-cxx-extension',
            '-Wno-error=void-pointer-to-enum-cast',
            '-Wno-error=unused-but-set-variable',
            '-Wno-error=unused-but-set-global',
            '-Wno-error=unused-but-set-parameter',
            '-Wno-error=deprecated-declarations',
            '-Wno-error=missing-designated-field-initializers',
            '-Wno-error=address-of-packed-member',
            '-Wno-error=cast-align',
            '-Wno-error=single-bit-bitfield-constant-conversion',
            '-Wno-error=cast-qual',
            '-Wno-error=sign-compare',
            '-Wno-error=pointer-bool-conversion',
            '-Wno-error=tautological-constant-compare',
        )),
        'OTHER_CXXFLAGS': ('-std=gnu++98 -fno-register-global-dtors-with-atexit '
                           '-mllvm -disable-atexit-based-global-dtor-lowering'),
        'CC': str(tools / 'x86_64-apple-darwin15-clang') + ' -std=gnu99',
        'CXX': tools / 'x86_64-apple-darwin15-clang',
        'LD': (str(tools / 'x86_64-apple-darwin15-clang') + ' -nostdlib -fuse-ld='
               + str(tools / 'x86_64-apple-darwin15-ld')),
        'MIG': tools / 'mig', 'MIGCOM': ROOT / 'toolchain/libexec/migcom',
        'STRIP': tools / 'x86_64-apple-darwin15-strip',
        'LIPO': tools / 'x86_64-apple-darwin15-lipo',
        'NM': tools / 'x86_64-apple-darwin15-nm',
        'LIBTOOL': tools / 'x86_64-apple-darwin15-libtool',
        'NMEDIT': tools / 'x86_64-apple-darwin15-nmedit',
        'UNIFDEF': shutil.which('unifdef'), 'HOST_CC': shutil.which('clang'),
        'HOST_FLEX': shutil.which('flex'), 'HOST_BISON': shutil.which('bison'),
        'HOST_GM4': shutil.which('m4'),
    }
    command = ['make', '-C', str(source), args.target]
    if args.target == 'link':
        configuration = objects / 'DEVELOPMENT_X86_64'
        variables.update({
            'CURRENT_KERNEL_CONFIG': 'DEVELOPMENT', 'CURRENT_ARCH_CONFIG': 'X86_64',
            'CURRENT_MACHINE_CONFIG': 'NONE',
            'CURRENT_BUILD_CONFIG': 'DEVELOPMENT^X86_64^NONE',
            'PRIMARY_BUILD_CONFIGS': 'DEVELOPMENT^X86_64^NONE',
            'SOURCE': source, 'RELATIVE_SOURCE_PATH': '.',
            'TARGET': str(configuration) + '/', 'OBJPATH': configuration,
        })
        command = ['make', '-C', str(configuration), '-f', str(source / 'Makefile'),
                   'do_build_kernel']
    result = subprocess.run(command + [f'{k}={v}' for k, v in variables.items()])
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
