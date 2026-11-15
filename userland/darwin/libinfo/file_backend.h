#ifndef COMMONPLACE_LIBINFO_FILE_BACKEND_H
#define COMMONPLACE_LIBINFO_FILE_BACKEND_H

#include <si_module.h>

extern si_mod_t *si_module_static_file(void);
#define si_search si_module_static_file
#define si_host_byname(m, n, f, i, e) ((m)->vtable->sim_host_byname((m), (n), (f), (i), (e)))
#define si_host_byaddr(m, a, f, i, e) ((m)->vtable->sim_host_byaddr((m), (a), (f), (i), (e)))
#define si_service_byname(m, n, p) ((m)->vtable->sim_service_byname((m), (n), (p)))
#define si_service_byport(m, n, p) ((m)->vtable->sim_service_byport((m), (n), (p)))

#endif
