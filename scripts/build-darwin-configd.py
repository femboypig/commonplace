#!/usr/bin/env python3
"""Build Apple's SystemConfiguration dynamic store and native Mach bindings."""

import shutil
from darwin_build import ROOT, OUT, archive, compile_source, link_program, prepare_source
from mach_interface import generate_interface


def main():
    source = prepare_source("configd")
    framework = source / "SystemConfiguration.fproj"
    include = OUT / "include/configd"
    public = include / "SystemConfiguration"
    public.mkdir(parents=True, exist_ok=True)
    for header in framework.glob("*.h"):
        shutil.copyfile(header, public / header.name)
    eap = include / "EAP8021X"
    eap.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "sources/eap8021x/EAP8021X.fproj/EAPClientProperties.h",
        eap / "EAPClientProperties.h")
    generated = OUT / "configd"
    interface = generate_interface("config", framework / "config.defs", generated,
        arch="x86_64", defines=("__LP64__",))
    helper = generate_interface("helper", framework / "helper/helper.defs", generated,
        arch="x86_64", defines=("__LP64__",))
    flags = [
        "-I" + str(include),
        "-I" + str(OUT / "include/security"),
        "-I" + str(OUT / "include/iokit-client"),
        "-I" + str(framework), "-I" + str(generated),
        "-I" + str(framework / "helper"),
        "-I" + str(source / "IPMonitorControl"),
        "-fblocks", "-DPRIVATE",
        "-DDEPLOYMENT_TARGET_MACOSX=1",
        "-DHAVE_OS_ACTIVITY=0",
        "-DHAVE_CRASHREPORTER=0",
        "-DHAVE_ASL_CONTROL_QUERY=0",
        "-DHAVE_SANDBOX_CHECKS=0", "-DHAVE_AUDIT_TOKEN_ACCESSORS=0",
        "-DHAVE_BUILTIN_PLUGINS=0", "-DHAVE_BUILTIN_INTERFACENAMER=1",
        "-DHAVE_BUILTIN_PREFERENCESMONITOR=1",
        "-DHAVE_BUILTIN_KERNELEVENTMONITOR=1", "-DHAVE_BUILTIN_LINKCONFIGURATION=1",
        "-idirafter", str(prepare_source("openbsm", "openbsm")),
        "-idirafter", str(prepare_source("openbsm", "openbsm") / "sys"),
        "-Wno-deprecated-declarations", "-Wno-deprecated-non-prototype",
    ]
    preferences = [framework / "SCP.c", *sorted(framework.glob("SCP[A-Z]*.c")),
        *sorted(framework.glob("SCPreferences*.c"))]
    network = [framework / name for name in (
        "SCNetworkConfigurationInternal.c", "SCNetworkInterface.c", "SCNetworkMigration.c",
        "SCNetworkProtocol.c", "SCNetworkService.c", "SCNetworkSet.c",
        "BondConfiguration.c", "BridgeConfiguration.c", "VLANConfiguration.c", "LinkConfiguration.c",
    )]
    paths = [*sorted(framework.glob("SCD*.c")), *preferences, *network,
        interface["user"], helper["user"], framework / "helper/SCHelper_client.c",
        framework / "SCSchemaDefinitions.c", framework / "dy_framework.c"]
    objects = [compile_source(path, OUT / "obj/configd-store" / (path.name + ".o"),
        flags) for path in paths]
    archive(OUT / "lib/libconfigd_store.a", objects)
    server = source / "configd.tproj"
    server_paths = [*sorted(server.glob("*.c")), server / "configd.m", interface["server"]]
    server_paths.extend(source / "Plugins" / name for name in (
        "InterfaceNamer/ifnamer.c", "PreferencesMonitor/prefsmon.c", "LinkConfiguration/linkconfig.c",
        "KernelEventMonitor/eventmon.c", "KernelEventMonitor/ev_extra.m",
        "KernelEventMonitor/ev_dlil.c", "KernelEventMonitor/ev_ipv4.c",
        "KernelEventMonitor/ev_ipv6.c", "common/cache.c",
    ))
    server_objects = [compile_source(path, OUT / "obj/configd" / (path.name + ".o"),
        [*flags, "-I" + str(server), "-I" + str(source / "Plugins/common"),
         "-x", "c", "-DMIG_SERVER_ROUTINE="])
        for path in server_paths]
    link_program(OUT / "bin/configd", server_objects, [
        OUT / "lib/libconfigd_store.a", OUT / "lib/libsectask.a", OUT / "lib/libbsm.a",
        OUT / "system/IOKit", OUT / "system/CoreFoundation",
    ])


if __name__ == "__main__":
    main()
