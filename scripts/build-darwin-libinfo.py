#!/usr/bin/env python3
"""Build local account lookups using Apple's Libinfo file parser and data model."""

from darwin_build import ROOT, OUT, compile_source, archive, prepare_source


def main():
    source = prepare_source("libinfo")
    directory = source / "lookup.subproj"
    flags = [
        "-I" + str(directory),
        "-fPIC",
        "-D__DYNAMIC__=1",
        "-include",
        "stdbool.h",
        "-DOSATOMIC_USE_INLINED=1",
        "-Wno-deprecated-declarations",
    ]
    objects = [
        compile_source(
            directory / name, OUT / "obj/libinfo" / name.replace(".c", ".o"), flags
        )
        for name in ("file_module.c", "si_data.c", "ils.c")
    ]
    objects.append(
        compile_source(
            source / "membership.subproj/membership.c",
            OUT / "obj/libinfo/membership.o",
            flags,
        )
    )
    objects.append(
        compile_source(
            ROOT / "userland/darwin/libinfo/accounts.c",
            OUT / "obj/libinfo/accounts.o",
            flags,
        )
    )
    original = (directory / "libinfo.c").read_text()
    section = original.split("/* misc */", 1)[1].split("/* no longer supported */", 1)[
        0
    ]
    derived = OUT / "derived/account_names.c"
    derived.parent.mkdir(parents=True, exist_ok=True)
    contents = (
        original[: original.index("#include")]
        + "#include <pwd.h>\n#include <grp.h>\n#include <stdio.h>\n"
        + section
    )
    if not derived.exists() or derived.read_text() != contents:
        derived.write_text(contents)
    objects.append(compile_source(derived, OUT / "obj/libinfo/account_names.o", flags))
    groups = original.split("static int\ngetgrouplist_internal", 1)[1].split(
        "/* XXX to do: async getgrouplist_2 */", 1
    )[0]
    group_source = OUT / "derived/group_list.c"
    preamble = (
        original[: original.index("#include")]
        + """#include <si_module.h>
#include <si_data.h>
#include <stdlib.h>
#include <limits.h>
extern si_mod_t *si_module_static_file(void);
extern si_item_t *commonplace_retain_groups(si_item_t *item);
static si_item_t *file_grouplist(si_mod_t *module, const char *name, uint32_t count)
{
    return module->vtable->sim_grouplist(module, name, count);
}
#define si_grouplist file_grouplist
#define si_search si_module_static_file
#define LI_set_thread_item(category, item) ((item) = commonplace_retain_groups(item))
static int
getgrouplist_internal"""
    )
    contents = preamble + groups
    if not group_source.exists() or group_source.read_text() != contents:
        group_source.write_text(contents)
    objects.append(
        compile_source(group_source, OUT / "obj/libinfo/group_list.o", flags)
    )
    archive(OUT / "lib/libsystem_info_file.a", objects)
    print("Darwin local account library: " + str(OUT / "lib/libsystem_info_file.a"))


if __name__ == "__main__":
    main()
