/* Local account API over Apple's Libinfo file backend. Retained lookup
 * results and enumeration cursors belong to the calling thread. */
#include <errno.h>
#include <pthread.h>
#include <si_data.h>
#include <si_module.h>
#include <stdlib.h>
extern si_mod_t *si_module_static_file(void);
uint32_t gL1CacheEnabled = 0;
struct account_state
{
    si_item_t *users[2], *groups[2], *supplementary_groups;
    si_list_t *user_list, *group_list;
};

static pthread_once_t account_once = PTHREAD_ONCE_INIT;
static pthread_key_t account_key;
static int account_key_error;

static void destroy_accounts(void *value)
{
    struct account_state *state = value;
    for (unsigned i = 0; i < 2; ++i)
    {
        si_item_release(state->users[i]);
        si_item_release(state->groups[i]);
    }
    si_item_release(state->supplementary_groups);
    si_list_release(state->user_list);
    si_list_release(state->group_list);
    free(state);
}

static void create_account_key(void)
{
    account_key_error = pthread_key_create(&account_key, destroy_accounts);
}

static struct account_state *get_accounts(void)
{
    int error = pthread_once(&account_once, create_account_key);
    if (!error)
        error = account_key_error;
    if (error)
    {
        errno = error;
        return NULL;
    }
    struct account_state *state = pthread_getspecific(account_key);
    if (state)
        return state;
    state = calloc(1, sizeof(*state));
    if (!state)
        return NULL;
    error = pthread_setspecific(account_key, state);
    if (error)
    {
        free(state);
        errno = error;
        return NULL;
    }
    return state;
}

si_item_t *commonplace_retain_groups(si_item_t *item)
{
    struct account_state *state = get_accounts();
    if (!state)
    {
        si_item_release(item);
        return NULL;
    }
    si_item_release(state->supplementary_groups);
    state->supplementary_groups = item;
    return item;
}

static void *retain_result(si_item_t **previous, si_item_t *item)
{
    si_item_release(*previous);
    *previous = item;
    return item ? item + 1 : NULL;
}
struct passwd *getpwuid(uid_t uid)
{
    struct account_state *state = get_accounts();
    if (!state)
        return NULL;
    si_mod_t *module = si_module_static_file();
    return retain_result(&state->users[0], module->vtable->sim_user_byuid(module, uid));
}
struct passwd *getpwnam(const char *name)
{
    struct account_state *state = get_accounts();
    if (!state)
        return NULL;
    if (!name)
    {
        errno = EINVAL;
        return NULL;
    }
    si_mod_t *module = si_module_static_file();
    return retain_result(&state->users[1], module->vtable->sim_user_byname(module, name));
}
struct group *getgrgid(gid_t gid)
{
    struct account_state *state = get_accounts();
    if (!state)
        return NULL;
    si_mod_t *module = si_module_static_file();
    return retain_result(&state->groups[0], module->vtable->sim_group_bygid(module, gid));
}
struct group *getgrnam(const char *name)
{
    struct account_state *state = get_accounts();
    if (!state)
        return NULL;
    if (!name)
    {
        errno = EINVAL;
        return NULL;
    }
    si_mod_t *module = si_module_static_file();
    return retain_result(&state->groups[1], module->vtable->sim_group_byname(module, name));
}
void setpwent(void)
{
    struct account_state *state = get_accounts();
    if (!state)
        return;
    si_mod_t *module = si_module_static_file();
    si_list_release(state->user_list);
    state->user_list = module->vtable->sim_user_all(module);
}
void endpwent(void)
{
    struct account_state *state = get_accounts();
    if (!state)
        return;
    si_list_release(state->user_list);
    state->user_list = NULL;
}
struct passwd *getpwent(void)
{
    struct account_state *state = get_accounts();
    if (!state)
        return NULL;
    if (!state->user_list)
        setpwent();
    si_item_t *item = si_list_next(state->user_list);
    return item ? (struct passwd *)(item + 1) : NULL;
}
int setpassent(int keep_open)
{
    struct account_state *state = get_accounts();
    if (!state)
        return 0;
    (void)keep_open;
    setpwent();
    return state->user_list != NULL;
}
void setgrent(void)
{
    struct account_state *state = get_accounts();
    if (!state)
        return;
    si_mod_t *module = si_module_static_file();
    si_list_release(state->group_list);
    state->group_list = module->vtable->sim_group_all(module);
}
void endgrent(void)
{
    struct account_state *state = get_accounts();
    if (!state)
        return;
    si_list_release(state->group_list);
    state->group_list = NULL;
}
struct group *getgrent(void)
{
    struct account_state *state = get_accounts();
    if (!state)
        return NULL;
    if (!state->group_list)
        setgrent();
    si_item_t *item = si_list_next(state->group_list);
    return item ? (struct group *)(item + 1) : NULL;
}
