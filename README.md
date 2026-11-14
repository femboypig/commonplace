# commonplace

commonplace is an independent operating system project built on darwin. it aims to develop its own userspace, system components, and desktop environment rather than replicate macos.

the project is under active development. no bootable system image is available yet.

## development

the current development target is `x86_64-apple-darwin15`, using xnu 3248.60.10.

## building

the build environment is intended for linux hosts.

## status

commonplace is in early development. current work focuses on the toolchain, xnu integration, and the foundations required to build an independent darwin-based system.

## upstream

commonplace uses open-source components published by apple and other upstream projects. source revisions are recorded in `sources.lock.json`.

commonplace is not affiliated with apple inc.

## credits

- apple for xnu, the darwin libraries and utilities, and the mach interface generator.
- the gnu bash contributors for the shell, built from apple's bash 3.2 sources.
- the llvm project for clang, compiler-rt, libc++, and libc++abi.
- tpoechtrager and the cctools-port contributors for the mach-o tools and linker used on linux.
- markmentovai for the mig compatibility headers used on linux.
- the openssl contributors for the cryptographic primitives used by the kernel.
- the hfsprogs and libdmg-hfsplus contributors for the tools used to build hfs+ disk images.
- the qemu contributors for the emulator used to boot and test the system.
