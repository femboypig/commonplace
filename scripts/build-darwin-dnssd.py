#!/usr/bin/env python3
"""Build Apple's DNS-SD socket client; the responder remains a separate service."""

from darwin_build import OUT, compile_source, archive, prepare_source


def main():
    source = prepare_source("mdns") / "mDNSShared"
    flags = [
        "-DPRIVATE",
        "-fblocks",
        "-DAPPLE_OSX_mDNSResponder=1",
        "-D_DNS_SD_LIBDISPATCH=1",
        "-I" + str(source),
        "-Wno-deprecated-declarations",
    ]
    objects = [
        compile_source(source / name, OUT / "obj/dnssd" / (name + ".o"), flags)
        for name in ("dnssd_clientlib.c", "dnssd_clientstub.c", "dnssd_ipc.c")
    ]
    archive(OUT / "lib/libdns_sd.a", objects)


if __name__ == "__main__":
    main()
