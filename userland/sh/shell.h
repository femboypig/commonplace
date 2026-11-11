#ifndef COMMONPLACE_SHELL_H
#define COMMONPLACE_SHELL_H
#include "runtime.h"
#define SHELL_WORDS 64
#define SHELL_COMMANDS 8
#define SHELL_ARGS 32
#define SHELL_LINE 1024

enum token_type { WORD, PIPE, INPUT, OUTPUT, APPEND };
struct token { enum token_type type; char *text; };
struct tokens { struct token values[SHELL_WORDS]; unsigned count; char storage[SHELL_LINE * 2]; };
struct command { char *argv[SHELL_ARGS + 1]; unsigned argc; char *input, *output; int append; };
struct pipeline { struct command commands[SHELL_COMMANDS]; unsigned count; };
struct expansion { int status; unsigned long pid; };
const char *shell_tokenize(const char *, struct tokens *, const struct expansion *);
const char *shell_parse(const struct tokens *, struct pipeline *);
int shell_is_builtin(const char *);
int shell_builtin(struct command *, int *exit_requested);
int shell_redirect(const struct command *);
int shell_execute(struct pipeline *, int *exit_requested);
void shell_prompt(void);
#endif
