/* Local account API over Apple's Libinfo file backend. No directory service
 * is needed for the initial static, single-threaded userspace. */
#include <errno.h>
#include <si_data.h>
#include <si_module.h>
extern si_mod_t *si_module_static_file(void);
uint32_t gL1CacheEnabled = 0;
static si_item_t *users[2], *groups[2];
static si_list_t *user_list, *group_list;

static void *retain_result(si_item_t **previous, si_item_t *item)
{
    si_item_release(*previous);
    *previous = item;
    return item ? item + 1 : NULL;
}
struct passwd *getpwuid(uid_t uid)
{
    si_mod_t *module = si_module_static_file();
    return retain_result(&users[0], module->vtable->sim_user_byuid(module, uid));
}
struct passwd *getpwnam(const char *name)
{
    if (!name) {
        errno = EINVAL;
        return NULL;
    }
    si_mod_t *module = si_module_static_file();
    return retain_result(&users[1], module->vtable->sim_user_byname(module, name));
}
struct group *getgrgid(gid_t gid)
{
    si_mod_t *module = si_module_static_file();
    return retain_result(&groups[0], module->vtable->sim_group_bygid(module, gid));
}
struct group *getgrnam(const char *name)
{
    if (!name) {
        errno = EINVAL;
        return NULL;
    }
    si_mod_t *module = si_module_static_file();
    return retain_result(&groups[1], module->vtable->sim_group_byname(module, name));
}
void setpwent(void)
{
    si_mod_t *module = si_module_static_file();
    si_list_release(user_list);
    user_list = module->vtable->sim_user_all(module);
}
void endpwent(void)
{
    si_list_release(user_list);
    user_list = NULL;
}
struct passwd *getpwent(void)
{
    if (!user_list)
        setpwent();
    si_item_t *item = si_list_next(user_list);
    return item ? (struct passwd *)(item + 1) : NULL;
}
int setpassent(int keep_open)
{
    (void)keep_open;
    setpwent();
    return user_list != NULL;
}
void setgrent(void)
{
    si_mod_t *module = si_module_static_file();
    si_list_release(group_list);
    group_list = module->vtable->sim_group_all(module);
}
void endgrent(void)
{
    si_list_release(group_list);
    group_list = NULL;
}
struct group *getgrent(void)
{
    if (!group_list)
        setgrent();
    si_item_t *item = si_list_next(group_list);
    return item ? (struct group *)(item + 1) : NULL;
}
