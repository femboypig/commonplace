#ifndef COMMONPLACE_INIT_H
#define COMMONPLACE_INIT_H
int init_console(int controlling);
void init_system(void);
void init_script(void);
int init_stopping(void);
char *const *init_environment(void);
#endif
