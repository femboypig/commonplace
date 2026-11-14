"""Collect upstream license text and source notices for the userspace bundle."""

import re

PROJECTS = (
    "bash",
    "hfs",
    "cf",
    "openpam",
    "pam_modules",
    "diskdev_cmds",
    "libresolv",
    "libc",
    "libinfo",
    "libplatform",
    "libm",
    "libutil",
    "copyfile",
    "removefile",
    "file_cmds",
    "text_cmds",
    "shell_cmds",
    "system_cmds",
    "architecture",
    "availabilityversions",
    "dyld",
    "libpthread",
    "libsystem",
    "libmalloc",
    "libclosure",
    "libcxx",
    "libcxxabi",
    "libunwind",
    "keymgr",
)


def write_notices(root, destination):
    sections = []
    seen = set()
    for project in PROJECTS:
        for source in sorted((root / "sources" / project).rglob("*")):
            if not source.is_file():
                continue
            if source.name in (
                "COPYING",
                "COPYRIGHT",
                "LICENSE",
                "LICENSE.TXT",
                "LICENSE.txt",
                "COPYING.TXT",
                "APPLE_LICENSE",
            ):
                notice = source.read_text(errors="replace")
            elif source.suffix in (".c", ".h", ".s", ".S", ".cpp", ".cxx", ".hpp"):
                content = source.read_text(errors="replace")
                match = re.match(
                    r"\s*(?:(?:/\*.*?\*/|//[^\n]*(?:\n|$))\s*)+", content, re.S
                )
                if not match or "copyright" not in match[0].lower():
                    continue
                notice = match[0].strip()
            else:
                continue
            if notice in seen:
                continue
            seen.add(notice)
            sections.append(str(source.relative_to(root)) + "\n\n" + notice)
    if not sections:
        raise ValueError("upstream license sources are missing")
    destination.write_text("\n\n".join(sections) + "\n")
