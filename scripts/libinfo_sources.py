"""Select original Libinfo routines for the local file-backed runtime."""


def account_names(original, network=None):
    section = original.split("/* misc */", 1)[1].split("/* no longer supported */", 1)[
        0
    ]
    contents = (
        original[: original.index("#include")]
        + "#include <pwd.h>\n#include <grp.h>\n#include <stdio.h>\n"
        + section
    )
    return contents


def group_list(original, network=None):
    groups = original.split("static int\ngetgrouplist_internal", 1)[1].split(
        "/* XXX to do: async getgrouplist_2 */", 1
    )[0]
    groups += (
        "int\ninitgroups"
        + original.split("int\ninitgroups", 1)[1].split("/* ALIAS */", 1)[0]
    )
    preamble = (
        original[: original.index("#include")]
        + """#include <si_module.h>
#include <si_data.h>
#include <stdlib.h>
#include <limits.h>
#include <sys/param.h>
#include <sys/kauth.h>
#include <unistd.h>
extern int __initgroups(u_int, gid_t *, int);
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
    return contents


def filesystem(original, network=None):
    filesystem = (
        original.split("/* FS */", 1)[1].split("mach_port_t\ngetfsspec_async_call", 1)[
            0
        ]
        + "struct fstab *\n"
        + "getfsfile"
        + original.split("struct fstab *\ngetfsfile", 1)[1].split(
            "mach_port_t\ngetfsfile_async_call", 1
        )[0]
    )
    filesystem += (
        "int\nsetfsent"
        + original.split("int\nsetfsent", 1)[1].split("/* GETADDRINFO */", 1)[0]
    )
    preamble = (
        original[: original.index("#include")]
        + """
#include <si_module.h>
#include <si_data.h>
#include <thread_data.h>
#include <fstab.h>
#include <stddef.h>
extern si_mod_t *si_module_static_file(void);
#define si_search si_module_static_file
#define si_fs_byspec(m, p) ((m)->vtable->sim_fs_byspec((m), (p)))
#define si_fs_byfile(m, p) ((m)->vtable->sim_fs_byfile((m), (p)))
#define si_fs_all(m) ((m)->vtable->sim_fs_all((m)))
"""
    )
    contents = preamble + filesystem
    return contents


def hosts(original, network=None):
    config = network.split("__private_extern__ int\nsi_inet_config", 1)[1].split(
        "void\nfreeaddrinfo", 1
    )[0]
    begin = config.index("\tif (net_config_token < 0)")
    end = config.index("\tstatus = 0;", begin)
    config = config[:begin] + config[end:]
    constants = network.split("#define SOCK_UNSPEC", 1)[1].split(
        "static int net_config_token", 1
    )[0]
    state = network.split("static uint32_t net_v4_count", 1)[1].split("// Libc SPI", 1)[
        0
    ]
    types = network.split("typedef struct {", 1)[1].split("__private_extern__ int", 1)[
        0
    ]
    hosts = original.split("void\nfreehostent", 1)[1].split(
        "struct hostent *\ngethostbynameerrno", 1
    )[0]
    lookup = original.split("struct hostent *\ngetipnodebyname(", 1)[1].split(
        "#if 0", 1
    )[0]
    contents = (
        original[: original.index("#include")]
        + """
#include <si_module.h>
#include <si_data.h>
#include <netdb.h>
#include <net/if.h>
#include <ifaddrs.h>
#include <arpa/inet.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
extern si_mod_t *si_module_static_file(void);
#define si_search si_module_static_file
#define si_host_byname(m,n,f,i,e) ((m)->vtable->sim_host_byname((m),(n),(f),(i),(e)))
#define SOCK_UNSPEC"""
        + constants
        + "static uint32_t net_v4_count"
        + state
        + "typedef struct {"
        + types
    )
    contents += (
        "int\nsi_inet_config" + config + network.split("/* getipnodebyname */", 1)[1]
    )
    contents += (
        "void\nfreehostent" + hosts + "struct hostent *\ngetipnodebyname(" + lookup
    )
    return contents


def account_reentrant(original, network=None):
    reentrant = (
        original[: original.index("#include")]
        + """
#include <si_module.h>
#include <si_data.h>
#include <errno.h>
#include <string.h>
extern si_mod_t *si_module_static_file(void);
#define si_search si_module_static_file
#define si_user_byname(m, n) ((m)->vtable->sim_user_byname((m), (n)))
#define si_user_byuid(m, n) ((m)->vtable->sim_user_byuid((m), (n)))
#define si_group_byname(m, n) ((m)->vtable->sim_group_byname((m), (n)))
#define si_group_bygid(m, n) ((m)->vtable->sim_group_bygid((m), (n)))
"""
    )
    for name, signature in (
        ("copy_user_r", "static int"),
        ("copy_group_r", "static int"),
        ("getpwnam_r", "int"),
        ("getpwuid_r", "int"),
        ("getgrnam_r", "int"),
        ("getgrgid_r", "int"),
    ):
        body = original.split(signature + "\n" + name + "(", 1)[1].split("\n}\n", 1)[0]
        reentrant += signature + "\n" + name + "(" + body + "\n}\n"
    return reentrant
