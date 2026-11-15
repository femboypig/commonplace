"""Configure Apple's published Libc diagnostics without private frameworks."""

from darwin_build import ROOT, OUT


def diagnostic_flags():
    directory = OUT / "include/libc-private"
    directory.mkdir(parents=True, exist_ok=True)
    header = directory / "CrashReporterClient.h"
    source = ROOT / "sources/libc_directories/include/CrashReporterClient.h"
    contents = source.read_bytes()
    if not header.exists() or header.read_bytes() != contents:
        header.write_bytes(contents)
    return ["-DLIBC_NO_LIBCRASHREPORTERCLIENT=1", "-I" + str(directory)]
